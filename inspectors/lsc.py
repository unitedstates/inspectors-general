#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.oig.lsc.gov
# Oldest report: 1994

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.oig.lsc.gov/rpts/audit.htm"
FINANCIAL_STATEMENTS_URL = "http://www.oig.lsc.gov/rpts/corp.htm"
OTHER_REPORTS_URL = "http://www.oig.lsc.gov/rpts/other.htm"
SEMIANNUAL_REPORTS_ULR = "http://www.oig.lsc.gov/sar/sar.htm"

REPORT_PUBLISHED_MAP = {
  '14-06': datetime.datetime(2014, 6, 30)
}

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for url in [SEMIANNUAL_REPORTS_ULR]:#OTHER_REPORTS_URL]:#FINANCIAL_STATEMENTS_URL, AUDIT_REPORTS_URL]:
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("blockquote > ul > a")
    if not results:
      results = doc.select("blockquote > ul > li > a")
    if not results:
      results = doc.select("blockquote > font > ul > a")
    if not results:
      results = doc.select("blockquote > a")
    for result in results:
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  if not result.text or result.text in [
    'PDF',
    'Word97',
    'WP5.1',
    'LSC Management Response',
    'Summary of Audit Findings and Recommendations',
  ]:
    # There are a few empty links due to bad html and some links for alternative
    # formats (PDF) that we will just ignore.
    return

  report_url = urljoin(landing_url, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  report_id = "-".join(report_id.split())

  title = "{} {}".format(result.text.strip(), result.next_sibling)

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    try:
      published_on_text = re.search('(\d+/\d+/\d+)', title).groups()[0]
    except AttributeError:
      try:
        published_on_text = re.search('(\w+ \d+, \d+)', title).groups()[0]
      except AttributeError:
        try:
          published_on_text = re.search('(\d+/\d+)', title).groups()[0]
        except AttributeError:
          # Since we only have the year, set this to Nov 1st of that year
          published_on_year = int(result.find_previous("h3").text)
          published_on = datetime.datetime(published_on_year, 11, 1)

    if not published_on:
      datetime_formats = [
        '%B %d, %Y',
        '%m/%d/%Y',
        '%m/%Y',
        '%m/%y'
      ]
      for datetime_format in datetime_formats:
        try:
          published_on = datetime.datetime.strptime(published_on_text, datetime_format)
        except ValueError:
          pass
        else:
          break

  if not published_on:
    import pdb;pdb.set_trace()

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'lsc',
    'inspector_url': 'http://www.oig.lsc.gov',
    'agency': 'lsc',
    'agency_name': 'Legal Services Corporation',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
