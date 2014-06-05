#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from utils import utils, inspector

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   pages - number of pages to fetch. defaults to all of them (using a very high number)
#
# Reports available since 2001
#
# Notes for IG's web team:
#   - Filters only work back through 2004, but there are documents back to 2001
#

BASE_URL = 'https://www.hudoig.gov/reports-publications/results'
BASE_REPORT_PAGE_URL = "https://www.hudoig.gov/"
ALL_PAGES = 1000

# TODO: There is a set of reports which don't have pdfs linked for some reason
MISSING_REPORT_IDS = [
  "2012-CH-1008",
  "2012-FO-0005",
  "2011-NY-1010",
  "IED-11-003M",
  "2010-LA-1012",
  "2010-AO-1003",
  "2008-LA-1010",
  "2007-NY-1006",
  "SAR 52",
]

UNRELEASED_TEXTS = [
  "not appropriate for public disclosure",
  "Report Not Available to the Public",
  "Not for public release",
]

def run(options):
  pages = options.get('pages', ALL_PAGES)
  year_range = inspector.year_range(options)

  for page in range(1, (int(pages) + 1)):
    logging.debug("## Downloading page %i" % page)

    url = url_for(year_range, page=page)
    index_body = utils.download(url)
    index = BeautifulSoup(index_body)

    rows = index.select('div.views-row')

    # If no more reports found, quit
    if not rows:
      break

    for row in rows:
      report = report_from(row, year_range)
      if report:
        inspector.save_report(report)

def report_from(report_row, year_range):
  published_date_text = report_row.select('span.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%B %d, %Y")

  landing_url_relative = report_row.select('a')[0]['href']
  landing_url = urljoin(BASE_REPORT_PAGE_URL, landing_url_relative)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("### Processing report %s" % landing_url)

  report_page_body = utils.download(landing_url)
  report_page = BeautifulSoup(report_page_body)

  article = report_page.select('article')[0]

  title = report_page.select('h1.title')[0].text
  report_type = article.select('div.field-name-field-pub-type div.field-item')[0].text

  try:
    report_id = article.select('div.field-name-field-pub-report-number div.field-item')[0].text.strip()
  except IndexError:
    # Sometimes the report_id is not listed on the page, so we fallback to
    # pulling it from the filename.
    report_filename = article.select('div.field-name-field-pub-document a')[0].text
    report_id = os.path.splitext(report_filename)[0]  # Strip off the extension

  try:
    report_url = article.select('div.field-name-field-pub-document a')[0]['href']
  except IndexError:
    report_url = None

  def get_optional_selector(selector):
    try:
      text = article.select(selector)[0].text.strip()
      # don't return empty strings
      if text:
        return text
      else:
        return None
    except IndexError:
      return None

  summary = get_optional_selector('div.field-type-text-with-summary')

  unreleased = False
  # Some reports are not available to the general public.
  for text_string in UNRELEASED_TEXTS:
    if text_string in title or (summary and text_string in summary):
      unreleased = True
      break

  program_area = get_optional_selector('div.field-name-field-pub-program-area div.field-item')
  state = get_optional_selector('div.field-name-field-pub-state div.field-item')
  funding = get_optional_selector('div.field-name-field-related-to-arra div.field-item')

  missing = False
  if not report_url and not unreleased:
    if report_id in MISSING_REPORT_IDS:
      missing = True
      unreleased = True
    else:
      raise AssertionError("Report: %s did not have a report url and is not unreleased" % landing_url)

  report = {
    'inspector': 'hud',
    'inspector_url': 'http://www.hudoig.gov/',
    'agency': 'hud',
    'agency_name': 'Housing and Urban Development',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'landing_url': landing_url,
    'type': report_type,
    'program_area': program_area,
    'state': state,
    'summary': summary,
    'funding': funding
  }

  # only include these if they are true
  if unreleased:
    report['unreleased'] = True
  if missing:
    report['missing'] = True

  return report

def url_for(year_range, page=1):
  start_year = year_range[0]
  end_year = year_range[-1]
  if start_year < 2004:
    # The website believes it doesn't have any reports before 2004. If we are
    # requesting before that time, remove all date filters and we will later
    # filter the results in memory
    start_year, end_year = '', ''
  return '%s?keys=&date_filter[min][year]=%s&date_filter[max][year]=%s&page=%i' % (BASE_URL, start_year, end_year, page-1)


utils.run(run) if (__name__ == "__main__") else None
