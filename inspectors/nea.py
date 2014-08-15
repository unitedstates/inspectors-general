#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://arts.gov/oig
# Oldest report: 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://arts.gov/oig/reports/audits"
SPECIAL_REVIEWS_URL = "http://arts.gov/oig/reports/specials"
SEMIANNUAL_REPORTS_URL = "http://arts.gov/oig/reports/semi-annual"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for url in [AUDIT_REPORTS_URL, SPECIAL_REVIEWS_URL, SEMIANNUAL_REPORTS_URL]:
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div.field-item li")
    for result in results:
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  link = result.find("a")
  if not link:
    return

  title = link.text
  report_url = urljoin(landing_url, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  try:
    published_on_text = title.split("-")[-1].split("–")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    published_on_year = int(result.find_previous("h3").text.strip())
    published_on = datetime.datetime(published_on_year, 11, 1)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nea',
    'inspector_url': 'http://arts.gov/oig',
    'agency': 'nea',
    'agency_name': 'National Endowment for the Arts',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
