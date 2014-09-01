#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.nasa.gov/
archive = 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - There are no reports available for 1996-1997.
# See http://oig.nasa.gov/audits/reports/FY96/index.html
# - The row for IG-11-007-R is misconfigured on
# http://oig.nasa.gov/audits/reports/FY11/tableData.html

AUDITS_REPORTS_URL = "http://oig.nasa.gov/audits/reports/FY{}/tableData.html"
OTHER_REPORT_URL = "http://oig.nasa.gov/investigations/reports.html"

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for year in year_range:
    url = AUDITS_REPORTS_URL.format(str(year)[2:4])
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("tr")
    for index, result in enumerate(results):
      if not index or not result.text.strip():
        # Skip the header row and any empty rows
        continue
      report = audit_report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

  # Pull the other reports
  doc = BeautifulSoup(utils.download(OTHER_REPORT_URL))
  results = doc.select("#subContainer ul li")
  for result in results:
    report = other_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def audit_report_from(result, landing_url, year_range):
  report_id = result.select("td")[0].text
  title = result.select("td")[1].text

  published_on_text = result.select("td")[2].text

  if report_id == 'IG-11-007-R':
    # See note to IG web team
    title = "“Information Technology Management Letter Comments"
    published_on = datetime.datetime(2010, 11, 16)
  else:
    try:
      published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%y')
    except ValueError:
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  report_url = urljoin(landing_url, result.select("td")[3].text.strip())
  unreleased = "foia" in report_url.lower() or "not available*" in report_url.lower()

  if unreleased:
    report_url = None

  if report_id == 'N/A':
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nasa',
    'inspector_url': 'http://oig.nasa.gov',
    'agency': 'nasa',
    'agency_name': 'National Aeronautics and Space Administration',
    'type': 'audit',
    'landing_url': landing_url,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  return report

def other_report_from(result, year_range):
  result_link = result.find("a")
  title = result_link.text

  published_on_text = result.find("strong").text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  report_url = result_link.get('href')
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nasa',
    'inspector_url': 'http://oig.nasa.gov',
    'agency': 'nasa',
    'agency_name': 'National Aeronautics and Space Administration',
    'type': 'other',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
