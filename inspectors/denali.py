#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.oig.denali.gov/
archive = 2006

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
  "Selected Contracting Authority Issues": datetime.datetime(2012, 3, 19), # OCR
  "Training event in 2009": datetime.datetime(2012, 6, 10), # OCR
  "Emerging energy technology fund": datetime.datetime(2013, 4, 11), # OCR

  "FY 2013, Second Half": datetime.datetime(2013, 10, 1), # OCR
  "FY 2013, First Half": datetime.datetime(2013, 5, 1), # img
  "FY 2012, Second Half": datetime.datetime(2012, 11, 1), # img
  "FY 2012, First Half": datetime.datetime(2012, 5, 1), # OCR
  "FY 2011, Second Half": datetime.datetime(2011, 11, 1), # img
  "FY 2011, First Half": datetime.datetime(2011, 5, 1), # OCR
  "FY 2010, Second Half": datetime.datetime(2010, 12, 1), # img
  "FY 2009, Second Half & FY 2010, First Half": datetime.datetime(2010, 6, 1), # img
  "FY 2009, First Half": datetime.datetime(2009, 5, 1), # img
  "FY 2008, Second Half": datetime.datetime(2008, 11, 1), # img
  "FY 2008, First Half": datetime.datetime(2008, 5, 1), # img
  "FY 2007, Second Half": datetime.datetime(2007, 11, 1), # img
  "FY 2007, First Half": datetime.datetime(2007, 5, 1), # img

  "IG-PAR-2012": datetime.datetime(2012, 11, 1), # OCR
  "IG-PAR-2011": datetime.datetime(2012, 1, 11), # OCR
  "IG-PAR-2010": datetime.datetime(2011, 1, 11), # img
  "IG-PAR-2007": datetime.datetime(2007, 11, 15), # img

  # Other report types are not tracked -
  #  The GAO comptroller decisions requested by IG are done by GAO
  #  The Audits of agency's financial statements have excerpts by the IG,
  #    that appear to already be present in the reports above.
}

def run(options):
  year_range = inspector.year_range(options, archive)

  doc = BeautifulSoup(utils.download(REPORTS_URL))
  results = doc.select("#mainContent blockquote a")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):

  # ignore GAO decisions requested by IG, and other annual audits
  header = result.parent.parent.find_previous_sibling("h4").text.strip().lower()
  if header.startswith("gao comptroller"):
    logging.debug("Skipping GAO comptroller report.");
    return
  elif header.startswith("annual audits of"):
    logging.debug("Skipping annual audits, redundant content.")
    return

  if header.startswith("inspection"):
    category = "inspection"
  elif header.startswith("semiannual"):
    category = "semiannual_report"
  else:
    category = "other"

  report_id = os.path.splitext(os.path.basename(result['href']))[0]
  report_url = urljoin(REPORTS_URL, result['href'])
  title = result.text.strip()

  if REPORT_PUBLISHED_MAPPING.get(title):
    published_on = REPORT_PUBLISHED_MAPPING.get(title)
  else:
    published_on = REPORT_PUBLISHED_MAPPING.get(report_id)

  if not published_on:
    raise Exception("Couldn't look up hardcoded report: %s, %s" % (title, report_id))

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
    'type': category,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
