#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm
# Oldest report: 2000

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add published dates for all reports in REPORT_PUBLISHED_MAPPING

REPORT_PUBLISHED_MAPPING = {
  "oig_auditreportp05": datetime.datetime(2014, 7, 17),
  "oigocoaudit2014": datetime.datetime(2014, 5, 1),
  "oigcommentletter042214": datetime.datetime(2014, 4, 22),
}

REPORTS_URL = "http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  results = doc.select("ul.text > ul > li")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  results = doc.select("ul.text td a")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  if result.name == 'a':
    link = result
  else:
    link = result.select("a")[-1]

  report_url = urljoin(REPORTS_URL, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  title = link.text

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    try:
      published_on_text = "/".join(re.search("(\w+) (\d+), (\d+)", title).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B/%d/%Y')
    except AttributeError:
      try:
        published_on_text = "/".join(re.search("(\w+) (\d+), (\d+)", str(link.next_sibling)).groups())
        published_on = datetime.datetime.strptime(published_on_text, '%B/%d/%Y')
      except AttributeError:
        # For reports where we can only find the year, set them to Nov 1st of that year
        published_on_year = int(re.search('(\d+)', title).groups()[0])
        published_on = datetime.datetime(published_on_year, 11, 1)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'cftc',
    'inspector_url': 'http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm',
    'agency': 'cftc',
    'agency_name': 'Commodity Futures Trading Commission',
    'file_type': 'pdf',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
