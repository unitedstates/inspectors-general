#!/usr/bin/env python

import datetime
import logging
import os
import re

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.neh.gov/about/oig
# Oldest report: 2000

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.neh.gov/about/oig/reviews"
SEMIANNUAL_REPORTS_URL = "http://www.neh.gov/about/oig/semi-annual-reports"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL))
  results = doc.select("table.views-table tr")
  for result in results:
    report = audit_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL))
  results = doc.select("table.views-table tr")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def audit_report_from(result, year_range):
  if result.parent.name == 'thead':
    # If we are a header row, skip
    return

  if len(result.select("td")) < 2:
    # If there aren't multiple columns, this is some sort of header row
    return

  title = result.select("td")[0].text

  published_on_text = result.select("span")[0].text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  report_link = result.find("a")
  if report_link:
    unreleased = False
    landing_url = None
    report_url = report_link.get('href')
    report_id = report_link.text.split()[0]
  else:
    unreleased = True
    report_url = None
    report_id = "{}-{}".format(published_on.date(), "-".join(title.split()))[:50]
    landing_url = AUDIT_REPORTS_URL

  report = {
    'inspector': "neh",
    'inspector_url': "http://www.neh.gov/about/oig",
    'agency': "neh",
    'agency_name': "National Endowment for the Humanities",
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  if landing_url:
    report['landing_url'] = landing_url
  return report

def semiannual_report_from(result, year_range):
  if result.parent.name == 'thead':
    # If we are a header row, skip
    return

  report_link = result.find("a")
  title = report_link.text

  report_url = report_link.get('href')
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  # Grab the last thing that looks like a date
  published_on_text = "-".join(re.findall('(\w+) (\d+), (\d{4})', title)[-1])
  published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "neh",
    'inspector_url': "http://www.neh.gov/about/oig",
    'agency': "neh",
    'agency_name': "National Endowment for the Humanities",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
