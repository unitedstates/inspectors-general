#!/usr/bin/env python

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
SEMIANNUAL_REPORTS_URL = "http://oig.federalreserve.gov/reports/semiannual-report-to-congress.htm"

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

REPORT_PUBLISHED_MAPPING = {
  "SAR_final_10_27_11": datetime.datetime(2011, 10, 27),
}

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  doc = beautifulsoup_from_url(REPORTS_URL)
  results = doc.select("#rounded-corner > tr")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("div.style-aside ul > li > a")
  for result in results:
    report_url = urljoin(BASE_PAGE_URL, result.get('href'))
    report = semiannual_report_from(report_url, year_range)
    if report:
      inspector.save_report(report)

  # The most recent semiannual report will be embedded on the main page
  report = semiannual_report_from(SEMIANNUAL_REPORTS_URL, year_range)
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
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'landing_url': landing_url,
    'topic': topic,
    'title': title,
    'summary': landing_page_text.strip(),
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  return report

def semiannual_report_from(report_url, year_range):
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on = REPORT_PUBLISHED_MAPPING.get(report_id)

  if extension != '.pdf':
    # If this is not a PDF, then it is actually a link to a landing page.
    # Grab the real report_url and the published date
    landing_url = report_url
    landing_page = beautifulsoup_from_url(landing_url)
    report_url_relative = landing_page.select("div.report-header-container-aside a")[0].get('href')
    report_url = urljoin(BASE_PAGE_URL, report_url_relative)

    published_on_text = landing_page.select("div.work-plan-container p strong")[0].text.split("–")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if not published_on:
    date_format = '%B%Y'
    try:
      published_on = datetime.datetime.strptime(report_id.split("_")[-1], date_format)
    except ValueError:
      report_date = report_id.replace("SAR", "").replace("web", "").replace("_", "").split("-")[-1]
      published_on = datetime.datetime.strptime(report_date, date_format)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Semiannual Report to Congress {}".format(published_on.date())

  return {
    'inspector': 'fed',
    'inspector_url': 'http://oig.federalreserve.gov',
    'agency': AGENCY_SLUGS['Board'],
    'agency_name': AGENCY_NAMES['Board'],
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'topic': 'Semiannual Report',
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None