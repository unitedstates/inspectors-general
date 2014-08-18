#!/usr/bin/env python

import datetime
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.gpo.gov/oig/
# Oldest report: 2004

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.cpb.org/oig/reports/"
SEMIANNUAL_REPORTS_URL = "http://www.cpb.org/oig/"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for url in [AUDIT_REPORTS_URL, SEMIANNUAL_REPORTS_URL]:
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div#content div#contentMain ul li.pdf a")
    if not results:
      raise AssertionError("No report links found for %s" % url)
    for result in results:
      if (not result.text.strip()):
        # Skip header rows
        continue
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  title = result.text
  report_id = result.get('href').split('/')[-1]
  report_url = urljoin(landing_url, result.get('href'))
  logging.debug("[%s] Building report...")

  if landing_url is AUDIT_REPORTS_URL:
    fragments = report_id.split('-')
    date_string = '%s-%s-%s' % (fragments[0], fragments[1], fragments[2])
    published_on = datetime.datetime.strptime(date_string, '%Y-%m-%d')
  else:
    print(report_id)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'cpb',
    'inspector_url': 'http://www.cpb.org/oig/reports/',
    'agency': 'cpb',
    'agency_name': 'Corporation for Public Broadcasting',
    'file_type': 'pdf',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'unreleased': False,
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
