#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.sigar.mil/
# Oldest report: 2008

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORT_URLS = [
  "http://www.sigar.mil/Newsroom/spotlight/spotlight.xml",
  "http://www.sigar.mil/Newsroom/testimony/testimony.xml",
  "http://www.sigar.mil/Newsroom/speeches/speeches.xml",
  "http://www.sigar.mil/audits/auditreports/reports.xml",
  "http://www.sigar.mil/audits/inspectionreports/inspection-reports.xml",
  "http://www.sigar.mil/audits/financialreports/Financial-Audits.xml",
  "http://www.sigar.mil/SpecialProjects/projectreports/reports.xml",
  "http://www.sigar.mil/Audits/alertandspecialreports/alert-special-reports.xml",
  "http://www.sigar.mil/quarterlyreports/index.xml",
]

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for report_url in REPORT_URLS:
    doc = BeautifulSoup(utils.download(report_url))
    results = doc.select("item")
    for result in results:
      report = report_from(result, report_url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  title = result.find("title").text.strip()

  report_url = urljoin(landing_url, result.find("link").next.strip())
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on_text = result.find("pubdate").text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%A, %B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'sigar',
    'inspector_url': "http://www.sigar.mil",
    'agency': 'sigar',
    'agency_name': "Special Inspector General for Afghanistan Reconstruction",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
