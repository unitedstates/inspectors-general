#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

#   inspector.save_report(report)

# http://www.cncsoig.gov
# Oldest report: <oldest_report_year>

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#
#

REPORTS_URLS = [
  'http://www.cncsoig.gov/news/semi-annual-reports',
  'http://www.cncsoig.gov/news/audit-reports',
  'http://www.cncsoig.gov/operations/investigations',
]

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for reports_page in REPORTS_URLS:
    doc = BeautifulSoup(utils.download(reports_page))
    results = doc.select("div#main div.whiteBox")
    if not results:
      raise AssertionError("No report links found for %s" % url)
    for result in results:
      report = report_from(result, reports_page, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  cell3 = result.find('div.cell3')
  if cell3: # it's a link to a separate page -- no PDF here
    release_page = urljoin(landing_url, cell3.find("a").get('href'))
    report_id, report_url, title, published_on = extract_from_release_page(release_page)

  report_url = urljoin(landing_url, result.find('div.cell4 a').get('href'))
  report_id = report_url.split('/')[-1].rstrip('.pdf')
  print(result)
  print(report_page)
  published_on = None

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'cncs',
    'inspector_url': 'http://www.cncsoig.gov',
    'agency': 'cncs',
    'agency_name': 'Corporation for National and Community Service',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),  # Date of publication
  }

  return report

def extract_from_release_page(url):
  doc = BeautifulSoup(utils.download(reports_page))
  body = doc.select("div#main div#lefSide")
  title = doc.select("h2").text
  return (report_id, report_url, title, published_on)

utils.run(run) if (__name__ == "__main__") else None
