#!/usr/bin/env python

import datetime
import logging
import os

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.peacecorps.gov/about/inspgen/
# Oldest report: 1989

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.peacecorps.gov/about/inspgen/reports/"

SECTION_TITLES_TO_SKIP = [
  "Management Advisory Reports",
  "Peer Reviews",
  "Special Reports/Reviews",
]

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  results = doc.select("li div li")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  link = result.find("a")
  report_url = link.get('href')
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  title = link.text

  section_title = result.find_previous("h3").text.strip()
  if section_title in SECTION_TITLES_TO_SKIP:
    return

  estimated_date = False
  try:
    published_on_text = title.split("–")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    published_on_year =int(section_title.lstrip("FY "))
    published_on = datetime.datetime(published_on_year, 11, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'peacecorps',
    'inspector_url': 'http://www.peacecorps.gov/about/inspgen/',
    'agency': 'peacecorps',
    'agency_name': 'Peace Corps',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

utils.run(run) if (__name__ == "__main__") else None
