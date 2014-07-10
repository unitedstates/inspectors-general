#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.doi.gov/oig/reports/index.cfm
# Oldest report: 1993

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - It would be nice to have topics for all reports

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
  year_range = inspector.year_range(options)

  response = utils.scraper.urlopen(REPORT_SEARCH_URL, method='POST', body=POST_DATA)
  doc = BeautifulSoup(response)

  results = doc.select("div.report")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  title = result.select("a span")[0].text.strip()

  report_url = urljoin(REPORT_URL_BASE, result.select("a")[0].get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  text_tuple = result.select("span")[1].text.split("|")
  published_on_text = text_tuple[0]
  topic_text = text_tuple[-1]

  if ':' in topic_text:
    topic = topic_text.split(":")[1].strip()
  else:
    # Some reports don't have topics
    topic = None
  published_on = datetime.datetime.strptime(published_on_text.strip(), 'Report Date: %m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  result = {
    'inspector': 'interior',
    'inspector_url': 'http://www.doi.gov/oig/index.cfm',
    'agency': 'interior',
    'agency_name': 'Department of the Interior',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if topic:
    result['topic'] = topic
  return result


utils.run(run) if (__name__ == "__main__") else None
