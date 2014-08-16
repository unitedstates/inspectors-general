#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.usitc.gov/oig/
# Oldest report: 1990

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.usitc.gov/oig/audit_reports.htm"
SEMIANNUAL_REPORTS_URL = "http://www.usitc.gov/oig/semiannual_reports.htm"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL))
  results = doc.select("div.text1 ul li")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  link = result.find("a", text=True)
  report_url = urljoin(AUDIT_REPORTS_URL, link.get('href'))
  report_id = "-".join(link.text.split())
  result_text = [x for x in result.stripped_strings]
  title = result_text[0]

  if not title or not report_id:
    import pdb;pdb.set_trace()

  # For reports where we can only find the year, set them to Nov 1st of that year
  published_on_year = int(result.find_previous("p").text)
  published_on = datetime.datetime(published_on_year, 11, 1)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'itc',
    'inspector_url': 'http://www.usitc.gov/oig/',
    'agency': 'itc',
    'agency_name': 'International Trade Commission',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
