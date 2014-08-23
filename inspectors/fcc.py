#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://transition.fcc.gov/oig/oigreportsaudit.html
# Oldest report: 1994

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:

AUDIT_REPORTS_URL = "http://transition.fcc.gov/oig/oigreportsaudit.html"
SEMIANNUAL_REPORTS_URL = "http://transition.fcc.gov/oig/oigreportssemiannual.html"
OTHER_REPORTS_URL = "http://transition.fcc.gov/oig/oigreportsletters.html"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "other": OTHER_REPORTS_URL,
}

def run(options):
  year_range = inspector.year_range(options)

  for report_type, url in REPORT_URLS.items():
    doc = beautifulsoup_from_url(url)
    results = doc.find_all("table", {"border": 2})[0].select("tr")
    for index, result in enumerate(results):
      if index < 2:
        # The first two rows are headers
        continue
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, page_url, report_type, year_range):
  if not result.text.strip():
    # Nothing in the entire row, just an empty row
    return

  report_url = urljoin(page_url, result.select("td a")[0].get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on_text = result.select("td")[0].text.split("\r\n")[0].strip()

  if len(result.select("td")) == 2:
    # Semiannual report
    published_on_text = published_on_text.split("to")[-1].split("through")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    title = "Semi-Annual Report - {}".format(published_on_text)
  else:
    try:
      published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%y')
    except ValueError:
      published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
    title = result.select("td")[1].text.strip()

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fcc',
    'inspector_url': 'http://fcc.gov/oig/',
    'agency': 'fcc',
    'agency_name': "Federal Communications Commission",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report


def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None