#!/usr/bin/env python

from utils import utils, inspector
from datetime import datetime
from urllib.parse import urljoin
import logging
import os.path
import re
import time

archive = 1997
#
# options:
#   standard since/year options for a year range to fetch from.
#
#   types - limit reports fetched to one or more types, comma-separated. e.g. "audit,testimony"
#          can include:
#             audit - Audit Reports
#             testimony - Congressional Testimony
#             news - News Releases
#             congress - Semiannual Report to Congress
#             whitepapers - White Papers
#             briefs - OIG Briefs
#             other - Other

# The report list is not stable, so sometimes we need to fetch the same page of
# results multiple times to get everything. This constant is the maximum number
# of times we will do so.
MAX_RETRIES = 10
REPORTS_PER_PAGE = 10


def run(options):
  report_types = options.get('types')
  if not report_types:
    report_types = "audit,testimony,news,congress,whitepapers,briefs,other"
  report_types = report_types.split(",")
  categories = [tup for tup in CATEGORIES if (tup[0] in report_types)]
  for category_name, category_id in categories:
    pages = get_last_page(options, category_id)

    rows_seen = set()
    pages_to_fetch = range(1, pages + 1)

    # While the reports themselves may shuffle around, the order of the dates
    # of the reports and how many of each date we see on each page will stay
    # constant. This dictionary will hold how many times we see each date.
    # We can stop retrying pages once we have as many unique reports for each
    # date as there are slots for that date.
    date_slot_counts = {}

    # This keeps track of how many unique reports we have found on each date,
    # for comparison with the numbers above.
    date_unique_report_counts = {}

    # This dict maps from a report date to a list of pages on which that date
    # was seen.
    date_to_pages = {}

    for retry in range(MAX_RETRIES):
      for page in pages_to_fetch:
        logging.debug("## Downloading %s, page %i, attempt %i" %
                      (category_name, page, retry))
        url = url_for(options, page, category_id)
        doc = utils.beautifulsoup_from_url(url)

        results = doc.select("tr")
        if not results:
          if ("Still can't find what you are searching for?" in
                  doc.select(".content")[0].text):
            # this search returned 0 results.
            pass
          else:
            # Otherwise, there's probably something wrong with the scraper.
            raise inspector.NoReportsFoundError("USPS %s" % category_name)
        for result in results:
          if not result.find("td"):
            # Header row
            continue
          if retry == 0:
            timestamp = get_timestamp(result)
            if timestamp in date_slot_counts:
              date_slot_counts[timestamp] = date_slot_counts[timestamp] + 1
            else:
              date_slot_counts[timestamp] = 1
              date_unique_report_counts[timestamp] = 0

            if timestamp in date_to_pages:
              if page not in date_to_pages[timestamp]:
                date_to_pages[timestamp].append(page)
            else:
              date_to_pages[timestamp] = [page]

          row_key = (str(result.text), result.a['href'])
          if row_key not in rows_seen:
            rows_seen.add(row_key)
            timestamp = get_timestamp(result)
            date_unique_report_counts[timestamp] = \
                date_unique_report_counts[timestamp] + 1

            report = report_from(result)
            inspector.save_report(report)

      pages_to_fetch = set()
      for date, report_count in date_unique_report_counts.items():
        if report_count < date_slot_counts[date]:
          for page in date_to_pages[date]:
            pages_to_fetch.add(page)
      if len(pages_to_fetch) == 0:
        break
      pages_to_fetch = list(pages_to_fetch)
      pages_to_fetch.sort()


def get_last_page(options, category_id):
  url = url_for(options, 1, category_id)
  doc = utils.beautifulsoup_from_url(url)
  return last_page_for(doc)


def get_timestamp(result):
  cells = result.select("td")
  return cells[0].text.strip()


# extract fields from HTML, return dict
def report_from(result):
  report = {
    'inspector': 'usps',
    'inspector_url': 'https://uspsoig.gov/',
    'agency': 'usps',
    'agency_name': 'United States Postal Service'
  }

  cells = result.select("td")
  report_type = type_for(cells[2].text.strip())

  published_on = datetime.strptime(get_timestamp(result), "%m/%d/%Y")

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")

  # if there's only one button, use that URL
  # otherwise, look for "Read Full Report" (could be first or last)
  link = cells[1].a
  landing_url = urljoin("https://uspsoig.gov/", link["href"])
  report['landing_url'] = landing_url

  landing_page = utils.beautifulsoup_from_url(landing_url)
  pdf_link = landing_page.find("a", text="View PDF")
  report_url = pdf_link["href"]
  report['url'] = report_url = pdf_link["href"]

  # get filename, use name as report ID, extension for type
  filename = os.path.basename(report_url)
  report['report_id'] = os.path.splitext(filename)[0]
  if (report_url == "https://uspsoig.gov/sites/default/files/"
          "document-library-files/2016/RARC-WP-16-001.pdf"):
    # Fix typo
    report['report_id'] = "RARC-WP-16-011"

  report['title'] = cells[1].a.text.strip()

  return report


def type_for(original_type):
  original = original_type.lower()
  if "audit" in original:
    return "audit"
  elif "testimony" in original:
    return "testimony"
  elif "news releases" in original:
    return "press"
  elif "congress" in original:
    return "congress"
  elif "white papers" in original:
    return "other"
  elif "oig briefs" in original:
    return "other"
  elif "other" in original:
    return "other"
  else:
    return None


# get the last page number, from the first page of search results
def last_page_for(doc):
  pager_last = doc.select("li.pager-last")
  if len(pager_last) == 0:
    return 1

  page = re.search("&page=(\\d+)(?:$|&)", pager_last[0].a["href"]).group(1)
  return int(page)


def url_for(options, page, category_id):
  year_range = inspector.year_range(options, archive)
  year_start = min(year_range)
  year_end = max(year_range)
  if category_id in ("94", "91", "93", "96"):
    # Always get all semiannual reports to congress, testimonies, news, and
    # "other" documents
    # This avoids false positives from the "no reports found" heuristic
    year_start = archive

  url = "https://uspsoig.gov/document-library"

  url += "?field_doc_date_value_op=between"
  url += "&field_doc_date_value[min][date]=%d" % year_start
  url += "&field_doc_date_value[max][date]=%d" % year_end

  url += "&field_document_type_tid[]=%s" % category_id

  # page is 0-indexed
  if page > 1:
    url += "&page=%i" % (page - 1)

  # Add a cache buster, this helps once we start retrying pages
  url += "&t=%i" % int(time.time())

  return url


CATEGORIES = [
  ('audit', '90'),
  ('testimony', '91'),
  ('news', '93'),
  ('congress', '94'),
  ('whitepapers', '95'),
  ('briefs' '92'),
  ('other', '96'),
]


utils.run(run) if (__name__ == "__main__") else None
