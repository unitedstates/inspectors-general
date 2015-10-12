#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.ftc.gov/about-ftc/office-inspector-general
archive = 1990

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add published dates for reports

AUDIT_REPORTS_URL = "http://www.ftc.gov/about-ftc/office-inspector-general/oig-reading-room/oig-audit-reports"
SEMIANNUAL_REPORTS_URL = "http://www.ftc.gov/about-ftc/office-inspector-general/oig-reading-room/semi-annual-reports-congress"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for report_type, url in REPORT_URLS.items():
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("li.views-row")
    if not results:
      raise inspector.NoReportsFoundError("FTC (%s)" % report_type)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  link = result.find("a")

  report_url = urljoin(landing_url, link.get('href').strip())
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  title = link.text

  file_type = None
  unreleased = False
  if "Non Public Report" in title.replace("-", " "):  # Normalize title for easier detection
    unreleased = True
    landing_url = report_url
    report_url = None
  elif not report_url.endswith(".pdf"):
    # A link to an html report
    file_type = "html"

  # Unfortunately we need to estimate the date since we only have the year
  estimated_date = False
  try:
    # For reports where we can only find the year, set them to Nov 1st of that year
    published_on_year = int(result.find_previous("h3").text.strip())
    published_on = datetime.datetime(published_on_year, 11, 1)
    estimated_date = True
  except AttributeError:
    published_on_year = int(re.search('Fiscal Year (\d+)', title).groups()[0])

    # For Spring reports, use April. For Fall reports, use October.
    if "First Half" in title:
      published_on_month = 4
    else:
      published_on_month = 10
    published_on = datetime.datetime(published_on_year, published_on_month, 1)


  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'ftc',
    'inspector_url': "http://www.ftc.gov/about-ftc/office-inspector-general",
    'agency': 'ftc',
    'agency_name': "Federal Trade Commission",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  if file_type:
    report['file_type'] = file_type
  return report

utils.run(run) if (__name__ == "__main__") else None
