#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.eac.gov/inspector_general/
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

CONGRESSIONAL_TESTIMONY_URL = "http://www.eac.gov/inspector_general/congressional_testimony.aspx"
HAVA_AUDITS_URL = "http://www.eac.gov/inspector_general/hava_funds_audits.aspx"
EAC_AUDITS_URL = "http://www.eac.gov/inspector_general/eac_audits_and_evaluations.aspx"
CONGRESSIONAL_REPORTS_URL = "http://www.eac.gov/inspector_general/congressional_reports.aspx"
INVESTIGATIONS_URL = "http://www.eac.gov/inspector_general/investigation_reports.aspx"
PEER_REVIEWS_URL = "http://www.eac.gov/inspector_general/peer_review_reports.aspx"

REPORT_URLS = {
  "testimony": CONGRESSIONAL_TESTIMONY_URL,
  "audit": HAVA_AUDITS_URL,
  "audit": EAC_AUDITS_URL,
  "congress": CONGRESSIONAL_REPORTS_URL,
  "investigation": INVESTIGATIONS_URL,
  "peer_review": PEER_REVIEWS_URL,
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, url in REPORT_URLS.items():
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div.mainRegion p a")
    if not results:
      raise AssertionError("No report links found for %s" % url)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def clean_text(text):
  return text.replace('\xa0', ' ').strip()

def report_from(result, landing_url, report_type, year_range):
  report_url = urljoin(landing_url, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  report_id = "-".join(report_id.split())

  title = clean_text(result.text)

  estimated_date = False
  try:
    published_on_text = "-".join(re.findall('(\w+) (\d+), (\d{4})', title)[-1])
    published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')
  except IndexError:
    try:
      published_on_text = "-".join(re.search('(\d+) (\w+) (\d{4})', title).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%d-%B-%Y')
    except AttributeError:
      # For reports where we can only find the year, set them to Nov 1st of that year
      published_on_year_text = clean_text(result.find_previous("h5").text)
      published_on_year = int(published_on_year_text.replace("Fiscal Year ", ""))
      published_on = datetime.datetime(published_on_year, 11, 1)
      estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'eac',
    'inspector_url': 'http://www.eac.gov/inspector_general/',
    'agency': 'eac',
    'agency_name': 'Election Assistance Commission',
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
