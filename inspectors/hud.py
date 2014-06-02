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
# Reports available since March 2004

BASE_URL = 'http://www.hudoig.gov/reports-publications/results'
BASE_REPORT_PAGE_URL = "http://www.hudoig.gov/"
ALL_PAGES = 1000

def run(options):
  pages = options.get('pages', ALL_PAGES)

  for page in range(1, (int(pages) + 1)):
    logging.debug("## Downloading page %i" % page)

    url = url_for(options, page=page)
    index_body = utils.download(url)
    index = BeautifulSoup(index_body)

    rows = index.select('div.views-row')

    # If no more reports found, quit
    if not rows:
      break

    for row in rows:
      report = report_from(row)
      if report:
        inspector.save_report(report)

def report_from(report_row):
  published_date_text = report_row.select('span.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%B %d, %Y")
  report_page_link_relative = report_row.select('a')[0]['href']
  report_page_link = urljoin(BASE_REPORT_PAGE_URL, report_page_link_relative)
  logging.debug("### Processing report %s" % report_page_link)

  report_page_body = utils.download(report_page_link)
  report_page = BeautifulSoup(report_page_body)

  article = report_page.select('article')[0]

  try:
    report_url = article.select('div.field-name-field-pub-document a')[0]['href']
  except:
    # Some reports are not available to the general public; just skipping for now
    # http://www.hudoig.gov/reports-publications/audit-reports/final-civil-action-%E2%80%93-fraudulent-expenses-paid-community
    logging.warning("[%s] Skipping report, not public." % report_page_link)
    return None

  title = report_page.select('h1.title a')[0].text
  report_type = article.select('div.field-name-field-pub-type div.field-item')[0].text

  try:
    report_id = article.select('div.field-name-field-pub-report-number div.field-item')[0].text
  except IndexError:
    # Sometimes the report_id is not listed on the page, so we fallback to
    # pulling it from the filename.
    report_filename = article.select('div.field-name-field-pub-document a')[0].text
    report_id = os.path.splitext(report_filename)[0]  # Strip off the extension

  def get_optional_selector(selector):
    try:
      return article.select(selector)[0].text
    except IndexError:
      return ""

  program_area = get_optional_selector('div.field-name-field-pub-program-area div.field-item')
  state = get_optional_selector('div.field-name-field-pub-state div.field-item')
  funding = get_optional_selector('div.field-name-field-related-to-arra div.field-item')
  summary = get_optional_selector('div.field-type-text-with-summary')

  return {
    'inspector': 'hud',
    'inspector_url': 'http://www.hudoig.gov/',
    'agency': 'hud',
    'agency_name': 'Housing and Urban Development',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'type': report_type,
    'program_area': program_area,
    'state': state,
    'funding': funding,
    'summary': summary,
  }

def url_for(options, page=1):
  year_range = inspector.year_range(options)

  start_year = year_range[0]
  end_year = year_range[-1]
  return '%s?keys=&date_filter[min][year]=%s&date_filter[max][year]=%s&page=%i' % (BASE_URL, start_year, end_year, page)


utils.run(run) if (__name__ == "__main__") else None
