#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# oldest year: 1998
#
# options:
#   standard since/year options for a year range to fetch from.
#
#   pages - number of pages to fetch. defaults to all of them (using a very high number)
#   begin - what page number to begin at. defaults to 1.
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

# This will actually get adjusted downwards on the fly, so pick a huge number.
# There are 164 pages total (page=163) as of 2014-07-27, so let's try, er, 1000.
ALL_PAGES = 1000


def run(options):
  year_range = inspector.year_range(options)
  pages = options.get('pages', ALL_PAGES)

  # default to starting at page 1
  begin = int(options.get('begin', 1))

  max_page = None
  for page in range(begin, (int(pages) + 1)):
    if max_page and (page > max_page):
      logging.debug("End of pages!")
      break

    logging.debug("## Downloading page %i" % page)
    url = url_for(options, page)
    body = utils.download(url)
    doc = BeautifulSoup(body)

    # When the USPS restores their page controls, we can use this again,
    # which saves one network call each time.
    max_page = last_page_for(doc)

    results = doc.select(".views-row")

    for result in results:
      report = report_from(result)

      # inefficient enforcement of --year arg, USPS doesn't support it server-side
      # TODO: change to published_on.year once it's a datetime
      if inspector.year_from(report) not in year_range:
        logging.warn("[%s] Skipping report, not in requested range." % report['report_id'])
        continue

      inspector.save_report(report)


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
  filename = link.split("/")[-1]
  extension = filename.split(".")[-1]
  report['report_id'] = filename.replace("." + extension, "")

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
# e.g. <li class="pager-item active last">158</li>
def last_page_for(doc):
  page = doc.select("li.pager-item.last")[0].text.replace("of ", "").strip()
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
  year_range = inspector.year_range(options)

  url = "https://uspsoig.gov/document-library?"

  # there's always a first year, and it defaults to current year
  since = "%s-01-01" % year_range[0]
  url += "&field_doc_date_value[value][date]=%s" % since

  only = options.get('types')
  if not only:
    only = "audit,congress,research"
  only = only.split(",")
  params = ["field_doc_cat_tid[]=%s" % CATEGORIES[id] for id in only]
  url += "&%s" % str.join("&", params)

  # they added this crazy thing
  annoying_prefix = "0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C"

  # page is 0-indexed
  if page > 1:
    url += "&page=%s%i" % (annoying_prefix, (page - 1))

  return url


CATEGORIES = {
  'audit': '1920',
  'testimony': '1933',
  'press': '1921',
  'research': '1922',
  'interactive': '3487',
  'congress': '1923'
}


utils.run(run) if (__name__ == "__main__") else None
