#!/usr/bin/env python

import datetime
import logging
import os
import re
import urllib

from utils import utils, inspector

# https://www.nlrb.gov/who-we-are/inspector-general
archive = 1989

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add a published date for 'OIG-F-16-12-01' on
# https://www.nlrb.gov/reports-guidance/reports/oig-audit-reports

AUDIT_REPORTS_URL = "https://www.nlrb.gov/reports-guidance/reports/oig-audit-reports"
AUDIT_REPORTS_ARCHIVE_URL = "https://www.nlrb.gov/reports-guidance/reports/oig-audit-reports/historical"
INSPECTION_REPORTS_URL = "https://www.nlrb.gov/reports-guidance/reports/oig-inspection-reports"
SEMIANNUAL_REPORTS_URL = "https://www.nlrb.gov/reports-guidance/reports/oig-semiannual-reports"

REPORT_PUBLISHED_MAP = {
  'OIG-F-16-12-01': datetime.datetime(2011, 12, 14),
  'OIG-AMR-25': datetime.datetime(1998, 9, 14),
  'OIG-AMR-20': datetime.datetime(1997, 9, 18),
  'OIG-AMR-19': datetime.datetime(1996, 9, 26),
  'OIG-AMR-18': datetime.datetime(1995, 9, 14),
  'OIG-AMR-17': datetime.datetime(1995, 3, 29),
  'OIG-AMR-16': datetime.datetime(1996, 6, 27),
  'OIG-AMR-15': datetime.datetime(1993, 2, 18),
  'OIG-AMR-14': datetime.datetime(1993, 2, 23),
  'OIG-AMR-13': datetime.datetime(1998, 9, 14),
  'OIG-AMR-12': datetime.datetime(1994, 7, 12),
  'OIG-AMR-10': datetime.datetime(1991, 2, 8),
  'OIG-AMR-5': datetime.datetime(1991, 6, 27),
  'OIG-AMR-4': datetime.datetime(1991, 6, 24),
  'OIG-AMR-2': datetime.datetime(1991, 5, 28),
}

REPORT_URLS = [
  ("audit", AUDIT_REPORTS_URL),
  ("audit", AUDIT_REPORTS_ARCHIVE_URL),
  ("inspection", INSPECTION_REPORTS_URL),
]


def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit and inspections reports
  for report_type, reports_url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(reports_url)
    results = doc.select("div.field-item")
    if not results:
      raise inspector.NoReportsFoundError("National Labor Relations Board (%s)" % report_type)
    for result in results:
      report = report_from(result, report_type, reports_url, year_range)
      if report:
        inspector.save_report(report)

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("div.field-item")
  if not results:
    raise inspector.NoReportsFoundError("National Labor Relations Board (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

ARCHIVE_PREAMBLE_TEXT = ("The following audit reports were issued more than "
                         "10 years ago.")

def report_from(result, report_type, base_url, year_range):
  link = result.find("a")
  if not link and result.text.strip() == ARCHIVE_PREAMBLE_TEXT:
    return

  report_url = urllib.parse.urljoin(base_url, link.get('href'))
  report_id, title = link.text.split(maxsplit=1)
  report_id = report_id.rstrip(":").rstrip(",")

  if report_url == AUDIT_REPORTS_ARCHIVE_URL:
    return

  title = title.strip()

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    for paren_text in re.findall('\((.*?)\)', title):
      try:
        published_on = datetime.datetime.strptime(paren_text, '%B %d, %Y')
        break
      except ValueError:
        pass
      try:
        published_on = datetime.datetime.strptime(paren_text, '%B %Y')
        break
      except ValueError:
        pass
  if not published_on:
    inspector.log_no_date("nlrb", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nlrb',
    'inspector_url': "https://www.nlrb.gov/who-we-are/inspector-general",
    'agency': 'nlrb',
    'agency_name': "National Labor Relations Board",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, year_range):
  link = result.find("a")
  report_url = link.get('href')
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  title = "Semiannual report - {}".format(link.text.strip())

  published_on_text = link.text.split("-")[-1].strip().replace(".pdf", "")
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nlrb',
    'inspector_url': "https://www.nlrb.gov/who-we-are/inspector-general",
    'agency': 'nlrb',
    'agency_name': "National Labor Relations Board",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
