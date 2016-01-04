#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# http://oig.ssa.gov/
archive = 1996

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

# This will actually get adjusted downwards on the fly, so pick a huge number.
# The largest one currently is Investigations with 55 pages as of 2014-08-05,
# so 1,000 should be good.
ALL_PAGES = 1000

AUDIT_REPORTS_URL = "http://oig.ssa.gov/audits-and-investigations/audit-reports/{year}-01--{year}-12?page={page}"
INVESTIGATIONS_REPORT_URL = "http://oig.ssa.gov/audits-and-investigations/investigations?page={page}"
SEMIANNUAL_REPORTS_URL = "http://oig.ssa.gov/newsroom/semiannual-reports?page={page}"
CONGRESSIONAL_TESTIMONY_URL = "http://oig.ssa.gov/newsroom/congressional-testimony?page={page}"
PERFORMANCE_REPORTS_URL = "http://oig.ssa.gov/newsroom/performance-reports?page={page}"

OTHER_REPORT_URLS = {
  "investigation": INVESTIGATIONS_REPORT_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "testimony": CONGRESSIONAL_TESTIMONY_URL,
  "performance": PERFORMANCE_REPORTS_URL,
}

BASE_REPORT_URL = "http://oig.ssa.gov/"

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  results_flag = False
  for year in year_range:
    report_type = 'audit'
    for page in range(0, ALL_PAGES):
      reports_found = reports_from_page(AUDIT_REPORTS_URL, page, report_type, year_range, year)
      if not reports_found:
        break
      else:
        results_flag = True
  if not results_flag:
    raise inspector.NoReportsFoundError("Social Security Administration (audit)")

  # Pull the other reports
  for report_type, report_format in OTHER_REPORT_URLS.items():
    for page in range(0, ALL_PAGES):
      reports_found = reports_from_page(report_format, page, report_type, year_range)
      if not reports_found:
        if page == 0:
          raise inspector.NoReportsFoundError("Social Security Administration (%s)" % report_type)
        else:
          break

def reports_from_page(url_format, page, report_type, year_range, year=''):
  url = url_format.format(page=page, year=year)
  doc = utils.beautifulsoup_from_url(url)
  results = doc.select("td.views-field")
  if not results:
    results = doc.select("div.views-row")
  if not results:
    return False

  for result in results:
    if not result.text.strip():
      # Skip empty rows
      continue
    report = report_from(result, report_type, year_range)
    if report:
      inspector.save_report(report)
  return True

visited_landing_urls = set()

def report_from(result, report_type, year_range):
  landing_page_link = result.find("a")
  title = landing_page_link.text.strip()
  landing_url = urljoin(BASE_REPORT_URL, landing_page_link.get('href'))

  # Sometimes the last report on one page is also the first report on the next
  # page. Here, we skip any duplicate landing pages we've already saved.
  if landing_url in visited_landing_urls:
    return

  # This landing page is a duplicate of another one
  if landing_url == "http://oig.ssa.gov/physical-security-office-disability-" \
        "adjudication-and-reviews-headquarters-building-limited-0":
    return

  published_on_text = result.select("span.date-display-single")[0].text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%A, %B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  try:
    report_id = result.select("span.field-data")[0].text.strip()
  except IndexError:
    report_id = landing_url.split("/")[-1]

  # This report has the wrong report number entered
  if landing_url == "http://oig.ssa.gov/audits-and-investigations/" \
        "audit-reports/congressional-response-report-internet-claim-" \
        "applications-0":
    report_id = "A-07-10-20166"

  landing_page = utils.beautifulsoup_from_url(landing_url)

  unreleased = False
  if "Limited Distribution" in title:
    unreleased = True
    report_url = None
  else:
    try:
      report_url = result.select("span.file a")[0].get('href')
    except IndexError:
      if not unreleased:
        try:
          report_url = landing_page.find("a", attrs={"type": 'application/octet-stream;'}).get('href')
        except AttributeError:
          unreleased = True
          report_url = None

  try:
    summary = landing_page.select("div.field-type-text-with-summary")[0].text.strip()
  except IndexError:
    summary = None

  file_type = None
  if report_url:
    _, extension = os.path.splitext(report_url)
    if not extension:
      file_type = 'html'

  visited_landing_urls.add(landing_url)

  report = {
    'inspector': "ssa",
    'inspector_url': "http://oig.ssa.gov",
    'agency': "ssa",
    'agency_name': "Social Security Administration",
    'type': report_type,
    'landing_url': landing_url,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  if file_type:
    report['file_type'] = file_type
  if summary:
    report['summary'] = summary
  return report

utils.run(run) if (__name__ == "__main__") else None
