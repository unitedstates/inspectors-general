#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.archives.gov/oig/
# Oldest report: 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.archives.gov/oig/reports/audit-reports-{year}.html"
SEMIANNUAL_REPORTS_URL = "http://www.archives.gov/oig/reports/semiannual-congressional.html"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for year in year_range:
    if year < 2006:  # The oldest year for audit reports
      continue
    url = AUDIT_REPORTS_URL.format(year=year)
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div#content li")
    for result in results:
      report = report_from(result, url, year, year_range)
      if report:
        inspector.save_report(report)

  # Pull the semiannual reports
  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL))
  results = doc.select("div#content li")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, landing_url, year, year_range):
  link = result.find("a")

  report_url = urljoin(landing_url, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  try:
    title = result.select("blockquote")[0].contents[0]
  except IndexError:
    title = result.text

  estimated_date = False
  try:
    published_on_text = re.search('(\w+ \d+, \d+)', result.text).groups()[0]
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except AttributeError:
    # Since we only have the year, set this to Nov 1st of that year
    published_on = datetime.datetime(year, 11, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'archives',
    'inspector_url': 'http://www.archives.gov/oig/',
    'agency': 'archives',
    'agency_name': 'National Archives and Records Administration',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

def semiannual_report_from(result, year_range):
  link = result.find("a")

  report_url = urljoin(SEMIANNUAL_REPORTS_URL, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  title = result.text.strip()
  published_on = datetime.datetime.strptime(title, '%B %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'archives',
    'inspector_url': 'http://www.archives.gov/oig/',
    'agency': 'archives',
    'agency_name': 'National Archives and Records Administration',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
