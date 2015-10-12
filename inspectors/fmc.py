#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.fmc.gov/bureaus_offices/office_of_inspector_general.aspx
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - The link to http://www.fmc.gov/userfiles/pages/file/OR10-03_UserFeeCalculations.pdf
# is incorrect. See `REPORT_URL_MAPPING`
# - Fix all links in `BLACKLIST_REPORT_URLS`

AUDIT_REPORTS_URL = "http://www.fmc.gov/about/oig_audits_evaluations_and_reviews.aspx"
SEMIANNUAL_REPORTS_URL = "http://www.fmc.gov/about/oig_semiannual_reports.aspx"

REPORT_URL_MAPPING = {
  "http://www.fmc.gov/userfiles/pages/file/OR10-03_UserFeeCalculations.pdf":
  "http://www.fmc.gov/assets/1/Page/OR10-03_UserFeeCalculations.pdf",
}

BLACKLIST_REPORT_URLS = [
  "http://www.fmc.gov/UserFiles/pages/File/FY_08_Audited_Financial_Statements_09-01.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Final_Report_09-01A.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Report_OR09-01.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Final_Report_A09-02.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Final_Report_A09-03.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Final_Report_A09-04.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Report_A09-05.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Final_Report_A09-06.pdf",
  "http://www.fmc.gov/UserFiles/pages/File/OIG_Final_Report_A09-07.pdf",
]

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL), "lxml")
  results = doc.select("table tr")
  if not results:
    raise inspector.NoReportsFoundError("Federal Maritime Commission (audits)")
  for index, result in enumerate(results):
    if not index:
      # Skip the header row
      continue
    report = report_from(result, AUDIT_REPORTS_URL, report_type='audit', year_range=year_range)
    if report:
      inspector.save_report(report)

  # Pull historical audits
  audit_year_links = doc.select("div.col-2-3 ul li a")
  for year_link in audit_year_links:
    audit_year_url = urljoin(AUDIT_REPORTS_URL, year_link.get('href'))
    doc = BeautifulSoup(utils.download(audit_year_url), "lxml")
    results = doc.select("table tr")
    if not results:
      # Grab results other than first and last (header and extra links)
      results = doc.select("div.col-2-2 ul")[1:-1]
    if not results:
      raise inspector.NoReportsFoundError("Federal Maritime Commission (%s)" % audit_year_url)
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = report_from(result, AUDIT_REPORTS_URL, report_type='audit', year_range=year_range)
      if report:
        inspector.save_report(report)

  # Pull the semiannual reports
  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL), "lxml")
  results = doc.select("div.col-2-2 p a") + doc.select("div.col-2-2 li a")
  if not results:
    raise inspector.NoReportsFoundError("Federal Maritime Commission (semiannual reports)")
  for result in results:
    report = report_from(result.parent, AUDIT_REPORTS_URL, report_type='semiannual_report', year_range=year_range)
    if report:
      inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  link = result.find("a")
  report_url = urljoin(landing_url, link.get('href'))
  title = link.text

  if report_url in REPORT_URL_MAPPING:
    report_url = REPORT_URL_MAPPING[report_url]

  if report_url in BLACKLIST_REPORT_URLS:
    return

  try:
    report_id = result.select("td")[0].text
  except IndexError:
    try:
      report_id = result.select("li")[0].text
    except IndexError:
      report_filename = report_url.split("/")[-1]
      report_id, _ = os.path.splitext(report_filename)

  estimated_date = False

  try:
    published_on_text = title.split("-")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    published_on_year = re.findall('\d+', report_id)[0]
    published_on = datetime.datetime.strptime("November 1, {}".format(published_on_year), '%B %d, %y')
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fmc',
    'inspector_url': 'http://www.fmc.gov/bureaus_offices/office_of_inspector_general.aspx',
    'agency': 'fmc',
    'agency_name': 'Federal Maritime Commission',
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
