#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# http://www.rrb.gov/oig/Default.asp
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.rrb.gov/oig/Library.asp"
AUDIT_REPORTS_URL = "http://www.rrb.gov/oig/reports/FY{year}reports.asp"


def run(options):
  year_range = inspector.year_range(options, archive)

  doc = utils.beautifulsoup_from_url(REPORTS_URL)

  # Pull the semiannual reports
  semiannul_results = doc.select("#AnnualManagementReports select")[0]
  for result in semiannul_results.select("option"):
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the special reports
  special_report_table = doc.find("table", attrs={"bordercolor": "#808080"})
  for index, result in enumerate(special_report_table.select("tr")):
    if not index:
      # Skip the header row
      continue
    report = report_from(result, REPORTS_URL, report_type='other', year_range=year_range)
    if report:
      inspector.save_report(report)

  # Pull the audit reports
  for year in year_range:
    if year < 2001:  # The oldest fiscal year page available
      continue
    year_url = AUDIT_REPORTS_URL.format(year=year)
    doc = utils.beautifulsoup_from_url(year_url)
    results = doc.select("#main table tr")
    if not results:
      raise inspector.NoReportsFoundError("Railroad Retirement Board (%d)" % year)
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = report_from(result, year_url, report_type='audit', year_range=year_range)
      if report:
        inspector.save_report(report)

saved_report_urls = set()


def report_from(result, landing_url, report_type, year_range):
  title = " ".join(result.select("td")[0].text.strip().split())

  published_on_text = result.select("td")[1].text.strip()
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%y')
  except ValueError:
    published_on = datetime.datetime.strptime(published_on_text, '%m/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  link = result.find("a")
  if link:
    unreleased = False
    report_url = urljoin(landing_url, link.get('href'))
    report_filename = report_url.split("/")[-1]
    report_id, _ = os.path.splitext(report_filename)

    # Deduplicate using report_url, "Reinvention 2001" is posted in both the
    # special reports table and the FY2001 audit reports
    if report_url in saved_report_urls:
      return
    saved_report_urls.add(report_url)

  else:
    unreleased = True
    report_url = None
    report_id = "{}-{}".format(published_on_text.replace("/", "-"), "-".join(title.split()))[:50]

  report = {
    'inspector': 'rrb',
    'inspector_url': "http://www.rrb.gov/oig/",
    'agency': 'rrb',
    'agency_name': "Railroad Retirement Board",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report


def semiannual_report_from(result, year_range):
  relative_report_url = result.get('value')
  if not relative_report_url:
    # Skip the header
    return

  # The links go up an extra level, not sure why.
  relative_report_url = relative_report_url.replace("../", "", 1)
  report_url = urljoin(REPORTS_URL, relative_report_url)
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  published_on_text = result.text.split(",")[0].strip()
  published_on = datetime.datetime.strptime(published_on_text, '%b %Y')
  title = "Semiannual Report - {}".format(published_on_text)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'rrb',
    'inspector_url': "http://www.rrb.gov/oig/",
    'agency': 'rrb',
    'agency_name': "Railroad Retirement Board",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
