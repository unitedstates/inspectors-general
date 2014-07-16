#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.usda.gov/oig/rptsaudits.htm
# Oldest report: 1978

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.usda.gov/oig/rptsaudits.htm"
SEMIANNUAL_REPORTS_URL = "http://www.usda.gov/oig/rptssarc.htm"
TESTIMONIES_URL = "http://www.usda.gov/oig/rptsigtranscripts.htm"

REPORT_PUBLISHED_MAPPING = {
  "TestimonyBlurb2": datetime.datetime(2004, 7, 14),
}

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  # doc = beautifulsoup_from_url(REPORTS_URL)
  # results = doc.select("#rounded-corner > tr")
  # for result in results:
  #   report = report_from(result, year_range)
  #   if report:
  #     inspector.save_report(report)

  for url in [SEMIANNUAL_REPORTS_URL, TESTIMONIES_URL]:
    doc = beautifulsoup_from_url(url)
    results = doc.select("ul li")
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, year_range):
  link = result.select("a")[0]
  title = link.text
  report_url = link.get('href')
  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]

  # These are just summary versions of other reports. Skip for now.
  if '508 Compliant Version' in title:
    return

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    try:
      published_on_text = result.select("span")[0].text.split("-")[0].strip()
    except IndexError:
      import pdb;pdb.set_trace()

    date_formats = ['%m/%d/%Y', '%m/%Y']
    published_on = None
    for date_format in date_formats:
      try:
        published_on = datetime.datetime.strptime(published_on_text, date_format)
      except ValueError:
        pass

  if published_on is None:
    import pdb;pdb.set_trace()

  report = {
    'inspector': 'agriculture',
    'inspector_url': 'http://www.usda.gov/oig/',
    'agency': 'agriculture', #AGENCY_SLUGS[agency],
    'agency_name': 'Department of Agriculture', #AGENCY_NAMES[agency],
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None