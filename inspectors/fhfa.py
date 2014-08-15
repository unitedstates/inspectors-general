#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://fhfaoig.gov/
# Oldest report: 2010

# options:
#   standard since/year options for a year range to fetch from.
#
#   pages - number of pages to fetch. defaults to all of them (using a very high number)
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://fhfaoig.gov/Reports/AuditsAndEvaluations?page={page}"

# This will actually get adjusted downwards on the fly, so pick a huge number.
# There are 4 pages of audits as of 2014-08-14, so let's try, er, 100.
ALL_PAGES = 100


def run(options):
  year_range = inspector.year_range(options)
  pages = options.get('pages', ALL_PAGES)

  # Pull the audit reports. Pages are 0-indexed.
  for page in range(0, int(pages) - 1):
    doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL.format(page=page)))
    results = doc.select("span.field-content")
    if not results:
      # No more results, we must have hit the last page
      break

    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, year_range):
  link = result.find("a")

  report_url = link.get('href')
  report_id = link.next_sibling.replace("(", "").replace(")", "").strip().rstrip("-").strip()
  title = link.text

  published_on_text = result.select("span.date-display-single")[0].text
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fhfa',
    'inspector_url': 'http://fhfaoig.gov',
    'agency': 'fhfa',
    'agency_name': "Federal Housing Financing Agency",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
