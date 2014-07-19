#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www2.ed.gov/about/offices/list/oig/areports.html
# Oldest report: 1995

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Fix the row for A17C0008 on
# http://www2.ed.gov/about/offices/list/oig/areports2003.html
# - Fix the published date for A06K0003
# on http://www2.ed.gov/about/offices/list/oig/areports2011.html

AUDIT_REPORTS_URL = "http://www2.ed.gov/about/offices/list/oig/areports{}.html"

REPORT_PUBLISHED_MAP = {
  "statelocal032002": datetime.datetime(2002, 3, 21),
  "statloc082001": datetime.datetime(2001, 8, 3),
  "A17B0006": datetime.datetime(2002, 2, 27),
  "A17A0002": datetime.datetime(2001, 2, 28),
  "A1790019": datetime.datetime(2000, 2, 28),  # Approximation
  "A17C0008": datetime.datetime(2003, 1, 31),
}

def run(options):
  year_range = inspector.year_range(options)

  # Get the audit reports
  for year in year_range:
    url = audit_url_for(year)
    doc = beautifulsoup_from_url(url)
    agency_tables = doc.find_all("table", {"border": 1})
    for agency_table in agency_tables:
      agency_name = agency_table.find_previous("p").text.strip()
      results = agency_table.select("tr")
      for index, result in enumerate(results):
        if not index:
          # First row is the header
          continue
        report = audit_report_from(result, agency_name, url, year_range)
        if report:
          inspector.save_report(report)

def audit_report_from(result, agency_name, page_url, year_range):
  if not result.text.strip():
    # Just an empty row
    return

  title = result.select("td")[0].text.strip()
  report_url = urljoin(page_url, result.select("td a")[0].get('href'))

  report_id = None
  if len(result.select("td")) != 3:
    report_id = result.select("td")[1].text.strip()
  if not report_id:
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    # See notes to the IG Web team for some of this
    published_on_text = result.select("td")[2].text.strip().replace(")", "").replace("//", "/")
    date_formats = ['%m/%d/%Y', '%m/%d/%y', '%m/%Y']
    published_on = None
    for date_format in date_formats:
      try:
        published_on = datetime.datetime.strptime(published_on_text, date_format)
      except ValueError:
        pass

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'education',
    'inspector_url': 'http://www2.ed.gov/about/offices/list/oig/',
    'agency': 'education',
    'agency_name': "Department of Education",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def audit_url_for(year):
  if year < 1998:
    # This is the first listed year
    year = 1998

  if year == 2001:
    # This one needs a capital A. Yup.
    return "http://www2.ed.gov/about/offices/list/oig/Areports2001.html"

  if year == datetime.datetime.today().year:
    # The current year is on the main page
    return AUDIT_REPORTS_URL.format("")
  else:
    return AUDIT_REPORTS_URL.format(year)

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None