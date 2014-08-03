#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.fdicoig.gov
# Oldest report: 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.fdicoig.gov/Search-Engine.asp"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  results = doc.find("table", {"cellpadding": "5"}).select("tr")
  for index, result in enumerate(results):
    if index < 3 or not result.text.strip():
      # The first three rows are headers
      continue
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  title = result.find("em").text.strip()

  unreleased = False
  try:
    report_url = urljoin(REPORTS_URL, result.select("a")[-1].get("href"))
  except IndexError:
    unreleased = True
    report_url = None
    landing_url = REPORTS_URL

  if report_url:
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)
  else:
    report_id = "-".join(title.split())[:50]

  published_on_text = result.select("td")[2].text
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
  except ValueError:
    logging.debug("[%s] Skipping since all real reports have published dates and this does not" % report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "fdic",
    'inspector_url': "http://www.fdicoig.gov",
    'agency': "fdic",
    'agency_name': "Federal Deposit Insurance Corporation",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
