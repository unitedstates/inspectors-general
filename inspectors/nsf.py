#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www.nsf.gov/oig/
# Oldest report: 1989

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - https://www.nsf.gov/oig/search/ encounters an error when using https.
# while it works if just using http.

# This needs to be HTTP, see note to IG Web team
CASE_REPORTS_URL = "http://www.nsf.gov/oig/search/results.cfm"

AUDIT_REPORTS_URL = "https://www.nsf.gov/oig/auditpubs.jsp"
SEMIANNUAL_REPORTS_URL = "https://www.nsf.gov/oig/semiannuals.jsp"

CASE_REPORTS_DATA = {
  'sortby': 'rpt_num',
  'sballfrm': 'Search',
}

REPORT_PUBLISHED_MAP = {
  "HSN_Summary": datetime.datetime(2013, 9, 30),  # Estimated
}

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL))
  results = doc.select("td.text table tr")
  for result in results:
    report = audit_report_from(result, year_range)
    if report:
      inspector.save_report(report)


  # Pull the case reports
  # response = utils.scraper.post(
  #   url=CASE_REPORTS_URL,
  #   data=CASE_REPORTS_DATA,
  # )
  # doc = BeautifulSoup(response.content)
  # results = doc.select("td.text table tr")
  # for index, result in enumerate(results):
  #   if not index or not result.text.strip():  # Skip the header row and empty rows
  #     continue
  #   report = case_report_from(result, CASE_REPORTS_URL, year_range)
  #   if report:
  #     inspector.save_report(report)

def audit_report_from(result, year_range):
  link = result.find("a")

  report_url = urljoin(AUDIT_REPORTS_URL, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  title = link.text

  last_column_node = result.select("td.tabletext")[-1]
  if last_column_node.text.strip():

    published_on_text, *report_id_text = last_column_node.stripped_strings
    if report_id_text:
      # If an explicit report_id is listed, use that.
      report_id = report_id_text[0]
    published_on = datetime.datetime.strptime(published_on_text.strip(), '%B %d, %Y')
  else:
    # No text in the last column. This is an incomplete row
    import pdb;pdb.set_trace()
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "nsf",
    'inspector_url': "https://www.nsf.gov/oig/",
    'agency': "nsf",
    'agency_name': "National Science Foundation",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report


def case_report_from(result, landing_url, year_range):
  link = result.find("a")

  report_url = urljoin(CASE_REPORTS_URL, link.get('href'))
  report_id = link.text
  title = result.contents[5].text

  published_on_text = result.contents[3].text
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "nsf",
    'inspector_url': "https://www.nsf.gov/oig/",
    'agency': "nsf",
    'agency_name': "National Science Foundation",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
