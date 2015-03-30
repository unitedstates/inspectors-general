#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import os.path

archive = 1998
#
# options:
#   standard since/year options for a year range to fetch from.
#
#   types - limit reports fetched to one or more types, comma-separated. e.g. "audit,testimony"
#          can include:
#             audit - Audit Reports
#             testimony - Congressional Testimony
#             press - Press Releases
#             research - Risk Analysis Research Papers
#             interactive - SARC (Interactive)
#             congress - Semiannual Report to Congress
#          defaults to
#             including audits, reports to Congress, and research
#             excluding press releases, SARC, and testimony to Congress

# The report list is not stable, so sometimes we need to fetch the same page of
# results multiple times to get everything. This constant is the maximum number
# of times we will do so.
MAX_RETRIES = 10
REPORTS_PER_PAGE = 10

def run(options):
  year_range = inspector.year_range(options, archive)
  pages = get_last_page(options)

  rows_seen = set()
  last_row_count = 0

  for page in reversed(range(1, pages + 1)):
    for retry in range(MAX_RETRIES):
      logging.debug("## Downloading page %i, attempt %i" % (page, retry))
      url = url_for(options, page)
      body = utils.download(url)
      doc = BeautifulSoup(body)

      results = doc.select(".views-row")
      if not results:
        raise inspector.NoReportsFoundError("USPS")
      for result in results:
        row_key = (str(result.text), result.a['href'])
        if row_key not in rows_seen:
          rows_seen.add(row_key)
          report = report_from(result)

          # inefficient enforcement of --year arg, USPS doesn't support it server-side
          # TODO: change to published_on.year once it's a datetime
          if inspector.year_from(report) not in year_range:
            logging.warn("[%s] Skipping report, not in requested range." % report['report_id'])
            continue

          inspector.save_report(report)

      if page == pages:
        # Since we're scraping the last page first, always fetch it only once.
        # If we lose a report between the last page and the second to last page,
        # we will see nine new reports on the second to last page, and then
        # retry that one until we get the tenth.
        break
      elif len(rows_seen) == last_row_count + REPORTS_PER_PAGE:
        # We saw as many new reports as we expected to, so we haven't missed
        # any, and it's safe to move on to the next page.
        break
      elif len(rows_seen) < last_row_count + REPORTS_PER_PAGE:
        # We were expecting more new reports on this page, try again
        continue
      else:
        raise AssertionError("Found %d new reports on page %d, too many!" % \
            (len(rows_seen) - last_row_count, page))
    last_row_count = len(rows_seen)

def get_last_page(options):
  url = url_for(options, 1)
  body = utils.download(url)
  doc = BeautifulSoup(body)
  return last_page_for(doc)

# extract fields from HTML, return dict
def report_from(result):
  report = {
    'inspector': 'usps',
    'inspector_url': 'https://uspsoig.gov/',
    'agency': 'usps',
    'agency_name': 'United States Postal Service'
  }

  pieces = result.select("span span")
  report_type = type_for(pieces[0].text.strip())

  if len(pieces) == 3:
    timestamp = pieces[2].text.strip()
    report['%s_id' % report_type] = pieces[1].text.strip()
  elif len(pieces) == 2:
    timestamp = pieces[1].text.strip()

  published_on = datetime.strptime(timestamp, "%m/%d/%Y")

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")

  # if there's only one button, use that URL
  # otherwise, look for "Read Full Report" (could be first or last)
  buttons = result.select("a.apbutton")
  if len(buttons) > 1:
    link = None
    for button in buttons:
      if "Full Report" in button.text:
        link = button['href']
  elif len(buttons) == 1:
    link = buttons[0]['href']
  report['url'] = link

  # get filename, use name as report ID, extension for type
  filename = os.path.basename(link)
  report['report_id'] = os.path.splitext(filename)[0]

  report['title'] = result.select("h3")[0].text.strip()

  return report

def type_for(original_type):
  original = original_type.lower()
  if "audit" in original:
    return "audit"
  elif "testimony" in original:
    return "testimony"
  elif "press release" in original:
    return "press"
  elif "research" in original:
    return "research"
  elif "sarc" in original:
    return "interactive"
  elif "report to congress":
    return "congress"
  else:
    return None

# get the last page number, from a page of search results
# e.g. <li class="pager-item active last">of 158</li>
def last_page_for(doc):
  pagers = doc.select("li.pager-item.last")
  if len(pagers) == 0:
    return 1

  page = pagers[0].text.replace("of ", "").strip()
  if page and len(page) > 0:
    return int(page)

  # this means we're on the last page, AFAIK
  else:
    return -1


# The USPS IG only supports a "since" filter.
# So, if we get a --year, we'll use it as "since", and then
# ignore reports after parsing their data (before saving them).
# Inefficient, but more efficient than not supporting --year at all.
def url_for(options, page=1):
  year_range = inspector.year_range(options, archive)

  url = "https://uspsoig.gov/document-library"

  # hidden input, always the same
  url += "?type=All"

  # there's always a first year, and it defaults to current year
  datetime_since = datetime(year=year_range[0], month=1, day=1)

  # Expected date format: 2015-02-26
  usps_formatted_datetime = datetime_since.strftime("%Y-%m-%d")
  url += "&field_doc_date_value[value][date]=%s" % usps_formatted_datetime

  only = options.get('types')
  if not only:
    only = "audit,congress,research"
  only = only.split(",")
  params = ["field_doc_cat_tid[]=%s" % id for (name, id) in CATEGORIES \
                                                        if (name in only)]
  url += "&%s" % str.join("&", params)

  # they added this crazy thing
  annoying_prefix = "0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C"

  # page is 0-indexed
  if page > 1:
    url += "&page=%s%i" % (annoying_prefix, (page - 1))

  return url


CATEGORIES = [
  ('audit', '1920'),
  ('testimony', '1933'),
  ('other', '3534'),
  ('press', '1921'),
  ('congress', '1923'),
  ('research', '1922'),
  ('other', '3557'),
]


utils.run(run) if (__name__ == "__main__") else None
