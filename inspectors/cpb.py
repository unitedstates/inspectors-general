#!/usr/bin/env python

import datetime
import re
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

ISSUED_DATE_EXTRACTION = re.compile('Issued ([A-Z][a-z]+ \d{1,2}, \d{4})')

REPORT_ID_DATE_EXTRACTION = [
  re.compile('.*(?P<month>\d{2})(?P<day>\d{2})(?P<year_2>\d{2})$'),
  re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[-_].*$'),
  re.compile('OIGPeerReview-(?P<year>\d{4})-(?P<month_name>\w+)$')
]

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for url in [AUDIT_REPORTS_URL, SEMIANNUAL_REPORTS_URL]:
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div#content div#contentMain ul li.pdf")
    if not results:
      raise AssertionError("No report links found for %s" % url)
    for result in results:
      if not result.find('a'):
        # Skip unlinked PDF's
        continue
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  print("\n\n")
  print(result)
  link = result.find('a')
  print(link)
  title = link.text
  report_id = link.get('href').split('/')[-1].rstrip('.pdf')
  report_url = urljoin(landing_url, link.get('href'))

  logging.debug("[%s] Building report..." % report_id)
  published_on = None
  issued_on = ISSUED_DATE_EXTRACTION.search(result.text)

  if issued_on:
    # year = issued_on.group('year')
    # month = issued_on.group('month')
    # day = issued_on.group('day')
    published_on = datetime.datetime.strptime(issued_on.group(1), '%B %d, %Y')
    print(published_on)
  else:
    published_on = extract_date_from_report_id(report_id)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    #return

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
  print(report)
  return report

def extract_date_from_report_id(report_id):
  published_on = ''

  for prog in REPORT_ID_DATE_EXTRACTION:
    match = prog.match(report_id)
    if match:

      year = ''
      try:
        year = '20%s' % match.group('year_2')
      except IndexError:
        year = match.group('year')

      month = ''
      try:
        month = datetime.datetime.strptime(match.group('month_name'), '%B').strftime('%m')
      except IndexError:
        month = match.group('month')

      day = ''
      try:
        day = match.group('day')
      except IndexError:
        day = '01' # Default to the first of the month.

      date_string = '%s-%s-%s' % (year, month, day)
      published_on = datetime.datetime.strptime(date_string, '%Y-%m-%d')

  print(published_on)
  return published_on

utils.run(run) if (__name__ == "__main__") else None
