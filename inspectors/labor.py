#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# https://www.oig.dol.gov/auditreports.htm
archive = 1979

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Fix published date for "Audit of The National Council on the Aging, INC.".
# Right now it just says "February 11" without a year.

AUDIT_REPORTS_URL = "https://www.oig.dol.gov/cgi-bin/oa_rpts-v4.cgi?s=&y={}&a=all"
SEMIANNUAL_REPORTS_URL = "https://www.oig.dol.gov/semiannual.htm"
BASE_URL = "https://www.oig.dol.gov"

REPORT_PUBLISHED_MAPPING = {
  "02-02-202-03-360": datetime.datetime(2002, 2, 11),
}

UNRELEASED_REPORT_IDS = [
  "24-08-004-03-330",
]

def run(options):
  year_range = inspector.year_range(options, archive)

  pre_1998_done = False
  results_flag = False

  # Pull the audit reports
  for year in year_range:
    if year < 1998:
      if pre_1998_done:
        continue
      else:
        pre_1998_done = True
    for page_number in range(0, 10000):
      year_url = url_for(year, page_number)
      doc = utils.beautifulsoup_from_url(year_url)
      results = doc.select("ol li")
      if not results:
        break
      else:
        results_flag = True
      for result in results:
        report = report_from(result, year_url)
        if report:
          inspector.save_report(report)

  if not results_flag:
    raise inspector.NoReportsFoundError("Department of Labor (audit reports)")

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("#content + div p a")
  if not results:
    raise inspector.NoReportsFoundError("Department of Labor (semiannal reports)")
  for result in results:
    if result.text == 'Highlights':
      continue
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_url):
  title = result.contents[0]
  landing_url = year_url  # No real landing pages
  report_id_text, published_text = result.contents[2].split("(")
  report_id = report_id_text.replace("Report No.", "").strip()
  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    published_text = published_text.rstrip(")")
    date_formats = ["%B %d, %Y", "%B %d,%Y", "%B %Y"]
    published_on = None
    for date_format in date_formats:
      try:
        published_on = datetime.datetime.strptime(published_text, date_format)
      except ValueError:
        pass

  report_url, summary_url, response_url = None, None, None
  for link in result.select("a"):
    if 'Report' in link.text:
      report_url = urljoin(BASE_URL, link.get('href'))
    elif 'Summary' in link.text:
      summary_url = urljoin(BASE_URL, link.get('href'))
    elif 'Response' in link.text:
      response_url = urljoin(BASE_URL, link.get('href'))

  # Fix incomplete URLs and report numbers
  if report_url == "https://www.oig.dol.gov/public/reports/oa/pre_1998/05-97-107-.pdf":
    report_url = "https://www.oig.dol.gov/public/reports/oa/pre_1998/05-97-107-10-105.pdf"
    report_id = "05-97-107-10-105"
  elif report_url == "https://www.oig.dol.gov/public/reports/oa/2001/2E--0002.pdf":
    report_url = "https://www.oig.dol.gov/public/reports/oa/2001/2E-10-105-0002.pdf"
    report_id = "2E-10-105-0002"

  UNRELEASED_TEXTS = [
    "This report will not be posted.",
    "This report contains Sensitive Information and will not be posted",
  ]
  if (report_id in UNRELEASED_REPORT_IDS
    or any(unreleased_text in result.text for unreleased_text in UNRELEASED_TEXTS)):
    unreleased = True
  else:
    unreleased = False

  report = {
    'inspector': 'labor',
    'inspector_url': 'https://www.oig.dol.gov',
    'agency': "labor",
    'agency_name': "Department of Labor",
    'report_id': report_id,
    'url': report_url,
    'landing_url': landing_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if summary_url:
    report['summary_url'] = summary_url
  if response_url:
    report['response_url'] = response_url
  if unreleased:
    report['unreleased'] = unreleased
  return report

def semiannual_report_from(result, year_range):
  published_on_text = result.text.split("-")[-1].strip()
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  trimmed_text = " ".join(result.text.split())  # Trim out any extra whitespace/newlines
  title = "Semiannual Report - {}".format(trimmed_text)
  published_on = datetime.datetime.strptime(published_on_text, '%B %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'labor',
    'inspector_url': 'https://www.oig.dol.gov',
    'agency': "labor",
    'agency_name': "Department of Labor",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def url_for(year, page_number):
  offset = page_number * 20  # 20 items per page
  if year < 1998:  # Everything before 1998 is clumped together
    year = "pre_1998"
  return AUDIT_REPORTS_URL.format("{}&next_i={}".format(year, offset))

utils.run(run) if (__name__ == "__main__") else None
