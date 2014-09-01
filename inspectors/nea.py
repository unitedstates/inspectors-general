#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://arts.gov/oig
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#   report_id: only bother to process a single report
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://arts.gov/oig/reports/audits"
SPECIAL_REVIEWS_URL = "http://arts.gov/oig/reports/specials"
SEMIANNUAL_REPORTS_URL = "http://arts.gov/oig/reports/semi-annual"
PEER_REVIEWS_URL = "http://arts.gov/oig/reports/external-peer-reviews"
FISMA_REPORTS_URL = "http://arts.gov/oig/reports/fisma"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "evaluation": SPECIAL_REVIEWS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "peer_review": PEER_REVIEWS_URL,
  "fisma": FISMA_REPORTS_URL,
}

def run(options):
  year_range = inspector.year_range(options, archive)

  only_report_id = options.get('report_id')

  # Pull the reports
  for report_type, url in REPORT_URLS.items():
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div.field-item li")
    for result in results:
      report = report_from(result, url, report_type, year_range)

      if report:
        # debugging convenience: can limit to single report
        if only_report_id and (report['report_id'] != only_report_id):
          continue

        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  link = result.find("a")
  if not link:
    return

  title = link.text
  report_url = urljoin(landing_url, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  estimated_date = False
  try:
    published_on_text = title.split("-")[-1].split("–")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    try:
      published_on_year = int(result.find_previous("h3").text.strip())
    except AttributeError:
      published_on_year = int(re.search('(\d+)', title).group())
    published_on = datetime.datetime(published_on_year, 11, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nea',
    'inspector_url': 'http://arts.gov/oig',
    'agency': 'nea',
    'agency_name': 'National Endowment for the Arts',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

utils.run(run) if (__name__ == "__main__") else None
