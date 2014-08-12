#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.pbgc.gov/
# Oldest report: 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://oig.pbgc.gov/evaluations/{year}.html"
BASE_REPORT_URL = "http://oig.pbgc.gov/"

HEADER_ROW_TEXT = [
  'Audits',
  'Evaluations',
  'Report Title',
]
PDF_REGEX = re.compile("\.pdf")

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for year in year_range:
    if year < 1998:  # The earliest year for audit reports
      continue
    year_url = AUDIT_REPORTS_URL.format(year=year)
    doc = BeautifulSoup(utils.download(year_url))
    results = doc.select("tr")
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, year_range):
  title = result.select("td")[0].text.strip()
  if title in HEADER_ROW_TEXT:
    # Skip the header rows
    return

  report_id = result.select("td")[1].text.replace("/", "-").replace(" ", "-")

  published_on_text = result.select("td")[2].text
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  link = result.find("a")
  landing_url = urljoin(BASE_REPORT_URL, link.get('href'))
  landing_page = BeautifulSoup(utils.download(landing_url))

  summary = " ".join(landing_page.select("div.holder")[0].text.split())
  report_link = landing_page.find("a", href=PDF_REGEX)
  if report_link:
    unreleased = False
    report_url = urljoin(landing_url, report_link.get('href'))
  else:
    unreleased = True
    report_url = None

  report = {
    'inspector': "pbgc",
    'inspector_url': "http://oig.pbgc.gov",
    'agency': "pbgc",
    'agency_name': "Pension Benefit Guaranty Corporation",
    'summary': summary,
    'landing_url': landing_url,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  return report

utils.run(run) if (__name__ == "__main__") else None
