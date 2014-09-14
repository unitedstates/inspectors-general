#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www.flra.gov/OIG
archive = 1999

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "https://www.flra.gov/IG_audit-reports"
INTERNAL_REVIEWS_URL = "https://www.flra.gov/IG_internal-reviews"
QA_REVIEWS_URL = "https://www.flra.gov/OIG_QA_Reviews"
SEMIANNUAL_REPORTS_URL = "https://www.flra.gov/IG_semi-annual_reports"
PEER_REVIEWS_URL = "https://www.flra.gov/OIG-PEER-REVIEW"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "inspection": INTERNAL_REVIEWS_URL,
  "inspection": QA_REVIEWS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "peer_review": PEER_REVIEWS_URL,
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, url in REPORT_URLS.items():
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div.node ul li")
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  title = result.text.strip()

  if 'Non-Public Report' in title:
    unreleased = True
    report_url = None
    report_id = "-".join(title.split())
    report_id = report_id.replace(":", "")
  else:
    unreleased = False
    link = result.find("a")
    # Some reports have incorrect relative paths
    relative_report_url = link.get('href').replace("../", "")
    report_url = urljoin(landing_url, relative_report_url)
    report_filename = report_url.split("/")[-1]
    report_id, _ = os.path.splitext(report_filename)

  estimated_date = False
  try:
    published_on = datetime.datetime.strptime(title, '%B %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    published_on_year = int(result.find_previous("p").text.strip())
    published_on = datetime.datetime(published_on_year, 11, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'flra',
    'inspector_url': 'https://www.flra.gov/OIG',
    'agency': 'flra',
    'agency_name': 'Federal Labor Relations Authority',
    'file_type': 'pdf',
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
  return report

utils.run(run) if (__name__ == "__main__") else None
