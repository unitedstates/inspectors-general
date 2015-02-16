#!/usr/bin/env python

import datetime
import logging
import os

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.state.gov/reports
archive = 2004

#
# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORT_TYPE_MAP = {
  "Audit": "audit",
  "Congressionally Mandated Report": "congress",
  "Evaluations and Special Projects": "evaluation",
  "Inspection": "inspection",
  "Management Alert": "other",
  "Semiannual Reports to Congress": "semiannual_report",
  "Strategic and Work Plans": "other",
}

BASE_URL = "http://oig.state.gov/reports?page={page}"
TESTIMONY_BASE_URL = "http://oig.state.gov/testimony-news?page={page}"
ALL_PAGES = 1000

def run(options):
  year_range = inspector.year_range(options, archive)
  pages = options.get('pages', ALL_PAGES)

  for page in range(0, int(pages)):
    logging.debug("## Downloading page %i" % page)

    url = BASE_URL.format(page=page)
    results = extract_reports_for_page(url, page, year_range, listing_xpath="div.row.report-listings-copy")
    if not results:
      break

  for page in range(0, int(pages)):
    logging.debug("## Downloading testimony page %i" % page)

    url = TESTIMONY_BASE_URL.format(page=page)
    results = extract_reports_for_page(url, page, year_range, listing_xpath="div.row.report-listings-data")
    if not results:
      break

def extract_reports_for_page(url, page_number, year_range, listing_xpath):
  body = utils.download(url)
  doc = BeautifulSoup(body)
  results = doc.select(listing_xpath)

  if not results and not page_number:
    # No link on the first page, raise an error
    raise AssertionError("No report links found for %s" % url)

  for result in results:
    report = report_from(result.parent, year_range)
    if report:
      inspector.save_report(report)
  return results

def report_from(result, year_range):
  title = result.find("h1").text
  report_url = result.select("span.file a")[0].get('href')
  logging.debug("## Processing report %s" % report_url)

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  try:
    published_on_text = list(result.select("div.is-darker-grey div.row")[0].strings)[4].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except ValueError:
    published_on_text = list(result.select("div.is-darker-grey div.row")[0].strings)[3].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  try:
    agency_name = result.select("div.row.report-listings-data div.callout span")[0].text
  except IndexError:
    agency_name = None

  if agency_name == 'BBG / Broadcasting Board of Governors':
    agency = 'bbg'
    agency_name = 'Broadcasting Board of Governors'
  else:
    agency = 'state'
    agency_name = 'Department of State'

  try:
    topic = result.select("div.row.report-listings-data div.callout span")[2].text
  except IndexError:
    topic = None

  try:
    report_type_name = list(result.select("div.is-darker-grey div.row")[3].strings)[5].strip()
    report_type = REPORT_TYPE_MAP.get(report_type_name, "other")
  except IndexError:
    report_type = "testimony"

  result = {
    'inspector': 'state',
    'inspector_url': 'http://oig.state.gov/',
    'agency': agency,
    'agency_name': agency_name,
    'report_id': report_id,
    'type': report_type,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if topic:
    result['topic'] = topic
  return result

utils.run(run) if (__name__ == "__main__") else None
