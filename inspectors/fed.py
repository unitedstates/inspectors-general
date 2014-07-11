#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.federalreserve.gov/reports/allyearsboardcfpb.htm
# Oldest report: 2007

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

BASE_PAGE_URL = "http://oig.federalreserve.gov/"
REPORTS_URL = "http://oig.federalreserve.gov/reports/allyearsboardcfpb.htm"

AGENCY_SLUGS = {
  'CFPB': "cfpb",
  'Board': "federal_reserve",
}
AGENCY_NAMES = {
  'CFPB': "Consumer Financial Protection Bureau",
  'Board': "Board of Governors of the Federal Reserve System",
}

UNRELEASED_TEXTS = [
  "our restricted report",
  "our reports in this area are generally restricted",
  "the report will not be posted to the public",
  "report will not be made available to the public",
]
UNRELEASED_LANDING_URLS = [
  # It may be an overstatement to call these unreleased.
  "http://oig.federalreserve.gov/reports/board_FMIC_loss_or_theft_confidential_jun2008.htm",
]

def run(options):
  year_range = inspector.year_range(options)
  doc = beautifulsoup_from_url(REPORTS_URL)

  results = doc.select("#rounded-corner > tr")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  title = result.select("a")[0].text
  agency = result.select("td.Col_Agency")[0].text
  topic = result.get('class')[0]
  landing_url = urljoin(BASE_PAGE_URL, result.select("a")[0].get('href'))
  published_on_text = result.select("td.Col_Date")[0].text
  published_on = datetime.datetime.strptime(published_on_text.strip(), '%m-%d-%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("Scraping landing url: %s", landing_url)
  landing_page = beautifulsoup_from_url(landing_url)

  landing_page_text = landing_page.select("div.style-report-text")[0].text

  # Some pages don't have any reports as a result
  if "did not issue any formal recommendations" in landing_page_text:
    return

  unreleased = any(unreleased_text in landing_page_text for unreleased_text in UNRELEASED_TEXTS)
  if landing_url in UNRELEASED_LANDING_URLS:
    unreleased = True

  if unreleased:
    report_id = None
    report_url = landing_url
  else:
    relative_report_url = landing_page.select("div.report-header-container-aside a")[-1].get('href')
    report_url = urljoin(BASE_PAGE_URL, relative_report_url)
    report_id = landing_page.select("span.report-number")[0].text.strip()

  if not report_id:
    # Fallback to the report filename
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)

  report = {
    'inspector': 'fed',
    'inspector_url': 'http://oig.federalreserve.gov',
    'agency': AGENCY_SLUGS[agency],
    'agency_name': AGENCY_NAMES[agency],
    'report_id': report_id,
    'url': report_url,
    'landing_url': landing_url,
    'topic': topic,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  return report

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None