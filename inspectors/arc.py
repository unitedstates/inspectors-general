#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.arc.gov/oig
# Oldest report: 2003

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.arc.gov/about/OfficeofInspectorGeneralAuditandInspectionReports.asp"
SEMIANNUAL_REPORTS_URL = "http://www.arc.gov/about/OfficeofinspectorGeneralSemiannualReports.asp"
PEER_REVIEWS_URL = "http://www.arc.gov/about/OfficeofInspectorGeneralExternalPeerReviewReports.asp"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for url in [AUDIT_REPORTS_URL, SEMIANNUAL_REPORTS_URL, PEER_REVIEWS_URL]:
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("table p > a")
    for result in results:
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  report_url = urljoin(landing_url, result.get('href'))
  report_url = report_url.replace("../", "")
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  try:
    title = result.parent.find("em").text
  except AttributeError:
    try:
      title = result.parent.contents[0].text
    except AttributeError:
      title = result.parent.contents[0]

  estimated_date = False
  try:
    published_on_text = title.split("–")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    try:
      published_on_year = int(result.find_previous("strong").text.replace("Fiscal Year ", ""))
    except AttributeError:
      published_on_year = int(result.text.split()[-1])
    published_on = datetime.datetime(published_on_year, 11, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'arc',
    'inspector_url': 'http://www.arc.gov/oig',
    'agency': 'arc',
    'agency_name': 'Appalachian Regional Commission',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

utils.run(run) if (__name__ == "__main__") else None
