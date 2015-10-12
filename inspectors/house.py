#!/usr/bin/env python

import datetime
import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://house.gov/content/learn/officers_and_organizations/inspector_general.php

archive = 2008

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#
#   Only Financial Audit reports are published -- it would be excellent to see other reports.
#   Financial Audit reports are published without any machine-readable publishing date. The
#     publishing date seems to only exist in the PDF itself, which can only unreliably be
#     read by a machine. Including the publishing date in the accompanying HTML or PDF filename
#     would be very helpful.
#

IG_URL = 'http://house.gov/content/learn/officers_and_organizations/inspector_general.php'

REPORT_ID_DATE_EXTRACTION = [
  re.compile('.*(?P<month>\d{2})(?P<day>\d{2})(?P<year_2>\d{2})$'),
  re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[-_].*$'),
  re.compile('OIGPeerReview-(?P<year>\d{4})-(?P<month_name>\w+)$'),
  re.compile('^(?P<month_and_year>\d{3,4})_'),
  re.compile('^annualplan(?P<year_2>\d{2})$'),
  re.compile('^Strategic-Plan-(?P<year>\d{4})-\d{4}$'),
]

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for url in [IG_URL]:
    doc = BeautifulSoup(utils.download(url), "lxml")
    results = doc.select("div.relatedContent ul.links li a")
    if not results:
      raise inspector.NoReportsFoundError("House of Representatives (%s)" % url)
    for result in results:
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  report_url = urljoin(landing_url, result.get('href'))
  report_id = report_url.split('/')[-1].rstrip('.pdf')
  title = result.text

  fiscal_year = re.search('FinalFY(\d{2})FSAReport', report_id).group(1)
  report_year = (int(fiscal_year) + 1)
  published_on = datetime.datetime.strptime('20%02d' % report_year, '%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'house',
    'inspector_url': IG_URL,
    'agency': 'house',
    'agency_name': 'House of Representatives',
    'file_type': 'pdf',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'estimated_date': True,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'unreleased': False,
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
