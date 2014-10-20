#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.doi.gov/oig/reports/index.cfm
archive = 1993

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - It would be nice to have topics for all reports
# - Some reports have wrong links. For example,
# http://www.doi.gov/oig/reports/upload/Report-of-Investigation---Pensus-Public.pdf
# is linked to when it should actually be
# http://www.doi.gov/oig/reports/upload/Report-of-Investigation-Pensus-Public.pdf

REPORT_URL_BASE = "http://www.doi.gov"
REPORT_SEARCH_URL = "http://www.doi.gov/oig/reports/index.cfm"
POST_DATA = {
  'reportKeyword': '',
  'reportNumber': '',
  'reportCategory': '',
  'reportType': '',
  'reportYear': '',
  'reportFiscalYear': '',
  'reportViewAll': 'View+All',
}

def run(options):
  year_range = inspector.year_range(options, archive)

  response = utils.scraper.urlopen(REPORT_SEARCH_URL, method='POST', body=POST_DATA)
  doc = BeautifulSoup(response)

  results = doc.select("div.report")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_type_from_text(report_type_text):
  if ':' in report_type_text:
    report_type_text = report_type_text.split(":")[1].strip()
  else:
    return 'other'

  if report_type_text in ['Audit', 'External Audit']:
    return 'audit'
  elif report_type_text == 'Investigation':
    return 'investigation'
  elif report_type_text in ['Inspection', 'Verification Review', 'Memorandum', 'Management Advisory', 'Advisory']:
    return 'inspection'
  elif report_type_text in ['Assessment', 'Evaluation']:
    return 'evaluation'
  elif report_type_text == 'Semiannual Report':
    return 'semiannual_report'
  else:
    return 'other'


def report_from(result, year_range):
  title = result.select("a span")[0].text.strip()

  report_url = urljoin(REPORT_URL_BASE, result.select("a")[0].get('href'))
  report_url = report_url.replace("---", "-")  # See note to IG team
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  text_tuple = result.select("span")[1].text.split("|")
  published_on_text = text_tuple[0]

  report_type_text = text_tuple[-1]
  report_type = report_type_from_text(report_type_text)

  published_on = datetime.datetime.strptime(published_on_text.strip(), 'Report Date: %m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  # These report entries are duplicates
  if report_id in ("2010-E-0003", "2008-E-0005", "2007-E-0019", "2007-E-0018") \
        and report_type == "other":
    return
  if report_id == "2008-G-0003" and \
        result.select("span")[2].text.strip().startswith("Our January 2003"):
    return
  if report_url == "http://www.doi.gov/oig/reports/upload/2003-E-0018.txt":
    return

  result = {
    'inspector': 'interior',
    'inspector_url': 'http://www.doi.gov/oig/',
    'agency': 'interior',
    'agency_name': 'Department of the Interior',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return result


utils.run(run) if (__name__ == "__main__") else None
