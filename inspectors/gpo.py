#!/usr/bin/env python

import datetime
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.gpo.gov/oig/
# Oldest report: 2004

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.gpo.gov/oig/audits.htm"
SEMIANNUAL_REPORTS_URL = "http://www.gpo.gov/oig/semi-anual.htm"

HEADER_TITLES = [
  'Report #',
  'Date',
]

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for url in [AUDIT_REPORTS_URL, SEMIANNUAL_REPORTS_URL]:
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div.section1 div.ltext > table tr")
    if not results:
      results = doc.select("td.three-col-layout-middle div.ltext > table tr")
    if not results:
      raise AssertionError("No report links found for %s" % url)
    for result in results:
      if (not result.text.strip() or
          result.find("th") or
          result.find("strong") or
          result.contents[1].text in HEADER_TITLES
        ):
        # Skip header rows
        continue
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  title = result.select("td")[-1].text

  if "contains sensitive information" in title:
    unreleased = True
    report_url = None
    report_id = "-".join(title.split())[:50]
  else:
    unreleased = False
    link = result.find("a")
    report_id = link.text
    report_url = urljoin(landing_url, link.get('href'))

  estimated_date = False
  try:
    published_on = datetime.datetime.strptime(report_id.strip(), '%m.%d.%y')
  except ValueError:
    published_on_year_text = result.find_previous("th").text
    published_on_year = int(published_on_year_text.replace("Fiscal Year ", ""))
    published_on = datetime.datetime(published_on_year, 11, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'gpo',
    'inspector_url': 'http://www.gpo.gov/oig/',
    'agency': 'gpo',
    'agency_name': 'Government Printing Office',
    'file_type': 'pdf',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
