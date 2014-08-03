#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.ssa.gov/
# Oldest report: 1996

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://oig.ssa.gov/audits-and-investigations/audit-reports/{year}-01--{year}-12?page={page}"
INVESTIGATIONS_REPORT_URL = "http://oig.ssa.gov/audits-and-investigations/investigations?page={page}"
SEMIANNUAL_REPORTS_URL = "http://oig.ssa.gov/newsroom/semiannual-reports?page={page}"
CONGRESSIONAL_TESTIMONY_URL = "http://oig.ssa.gov/newsroom/congressional-testimony?page={page}"
PERFORMANCE_REPORTS_URL = "http://oig.ssa.gov/newsroom/performance-reports?page={page}"

OTHER_REPORT_URLS = [
  PERFORMANCE_REPORTS_URL,
  CONGRESSIONAL_TESTIMONY_URL,
  SEMIANNUAL_REPORTS_URL,
  INVESTIGATIONS_REPORT_URL,
]

BASE_REPORT_URL = "http://oig.ssa.gov/"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for year in year_range:
    for page in range(0, 999):
      url = AUDIT_REPORTS_URL.format(year=year, page=page)
      doc = BeautifulSoup(utils.download(url))
      results = doc.select("td.views-field")
      if not results:
        break

      for result in results:
        report = report_from(result, year_range)
        if report:
          inspector.save_report(report)

  # Pull the other reports
  for report_format in OTHER_REPORT_URLS:
    for page in range(0, 999):
      url = report_format.format(page=page)
      doc = BeautifulSoup(utils.download(url))
      results = doc.select("td.views-field")
      if not results:
        results = doc.select("div.views-row")
      if not results:
        break

      for result in results:
        if not result.text.strip():
          # Skip empty rows
          continue
        report = report_from(result, year_range)
        if report:
          inspector.save_report(report)

def report_from(result, year_range):
  landing_page_link = result.find("a")
  title = landing_page_link.text.strip()
  landing_url = urljoin(BASE_REPORT_URL, landing_page_link.get('href'))

  unreleased = False
  if "Limited Distribution" in title:
    unreleased = True
    report_url = None

  published_on_text = result.select("span.date-display-single")[0].text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%A, %B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  try:
    report_id = result.select("span.field-data")[0].text.strip()
  except IndexError:
    report_id = landing_url.split("/")[-1]

  try:
    report_url = result.select("span.file a")[0].get('href')
  except IndexError:
    if not unreleased:
      landing_page = BeautifulSoup(utils.download(landing_url))
      try:
        report_url = landing_page.find("a", attrs={"type": 'application/octet-stream;'}).get('href')
      except AttributeError:
        report_url = landing_url

  file_type = None
  if report_url:
    _, extension = os.path.splitext(report_url)
    if not extension:
      file_type = 'html'

  report = {
    'inspector': "ssa",
    'inspector_url': "http://oig.ssa.gov",
    'agency': "ssa",
    'agency_name': "Social Security Administration",
    'landing_url': landing_url,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  if file_type:
    report['file_type'] = file_type
  return report

utils.run(run) if (__name__ == "__main__") else None
