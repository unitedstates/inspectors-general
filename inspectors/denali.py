#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.oig.denali.gov/
# Oldest report: 2006?

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#   - many reports could use some OCRing, or re-upload in their original form.

REPORTS_URL = "http://www.oig.denali.gov"

# a bunch of hardcoded dates for published dateless reports
REPORT_PUBLISHED_MAPPING = {
  "Buckland": datetime.datetime(2006, 9, 1), # img
  "Chitina": datetime.datetime(2008, 10, 1), # img
  "Gustavus": datetime.datetime(2013, 4, 5), # OCR
  "Ketchikan": datetime.datetime(2010, 7, 1), # OCR
  "Manokotak": datetime.datetime(2006, 9, 1), # img
  "McGrath": datetime.datetime(2009, 9, 1), # img
  "Nikiski": datetime.datetime(2008, 9, 1), # img
  "Port Graham": datetime.datetime(2009, 9, 1), # img
  "Red Devil": datetime.datetime(2007, 1, 1),# img
  "Sterling Landing": datetime.datetime(2007, 1, 1), # img
  "Stony River": datetime.datetime(2007, 1, 1), # img
  "Takotna": datetime.datetime(2007, 1, 1), # img
  "Tanacross": datetime.datetime(2009, 10, 1), # OCR
  "Tenakee Springs": datetime.datetime(2006, 9, 1), # img
  "Togiak": datetime.datetime(2009, 9, 1), # img
  "Unalakleet": datetime.datetime(2007, 1, 1), # img
  "Village Resume Project": datetime.datetime(2012, 2, 9), # OCR
  "Selected Contacting Authority Issues": datetime.datetime(2012, 3, 19), # OCR
  "Training event in 2009": datetime.datetime(2012, 6, 10), # OCR
  "Emerging energy technology fund": datetime.datetime(2013, 4, 11) # OCR
}

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  results = doc.select("some-selector")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

# suggested: a function that gets report details from a parent element,
# extract a dict of details that are ready for inspector.save_report().
def report_from(result, year_range):
  report_id = <report_id>
  report_url = <report_url>
  title = <title>
  published_on = <published_on>

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "denali",
    'inspector_url': "http://www.oig.denali.gov",
    'agency': "denali",
    'agency_name': "Denali Commission",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
