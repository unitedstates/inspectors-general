#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector, admin

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

REPORT_PUBLISHED_MAP = {
  "508letterOIG2016": datetime.datetime(2016, 5, 27),
  "A16-01": datetime.datetime(2015, 11, 10),
  "A16-02": datetime.datetime(2015, 11, 12),
  "A15-01": datetime.datetime(2014, 11, 14),
  "A15-01A": datetime.datetime(2014, 12, 31),
  "A15-02": datetime.datetime(2014, 11, 14),
  "A15-03": datetime.datetime(2014, 11, 14),
  "A15-04": datetime.datetime(2015, 3, 10),
  "A15-05": datetime.datetime(2015, 9, 25),
  "A14-01": datetime.datetime(2013, 12, 12),
  "A14-01A": datetime.datetime(2014, 1, 31),
  "A14-02": datetime.datetime(2014, 1, 3),
  "A13-01": datetime.datetime(2012, 11, 6),
  "A13-02": datetime.datetime(2012, 12, 6),
  "A13-03": datetime.datetime(2012, 12, 21),
  "A13-04": datetime.datetime(2012, 12, 14),
  "A13-04A": datetime.datetime(2013, 3, 15),
  "A12-01": datetime.datetime(2011, 11, 9),
  "A12-02": datetime.datetime(2012, 1, 17),
  "OR12-01": datetime.datetime(2012, 3, 2),
  "A12-01A": datetime.datetime(2012, 3, 5),
  "OR12-02": datetime.datetime(2012, 7, 17),
  "OR11-02": datetime.datetime(2011, 9, 30),
  "OR11-01": datetime.datetime(2011, 3, 16),
  "A11-02A": datetime.datetime(2011, 1, 31),
  "A11-02": datetime.datetime(2010, 11, 10),
  "A11-01A": datetime.datetime(2010, 11, 8),
  "A11-01": datetime.datetime(2010, 12, 15),
  "OR10-04": datetime.datetime(2010, 8, 6),
  "OR10-03": datetime.datetime(2010, 5, 27),
  "OR10-02": datetime.datetime(2010, 5, 14),
  "A10-01": datetime.datetime(2009, 11, 6),
  "A10-01A": datetime.datetime(2010, 3, 2),
  "OR10-01": datetime.datetime(2010, 3, 4),
  "A10-02": datetime.datetime(2010, 1, 28),
  "A10-03": datetime.datetime(2010, 3, 1),
  "A09-01": datetime.datetime(2008, 11, 6),
  "A09-01A": datetime.datetime(2009, 1, 15),
  "OR09-01": datetime.datetime(2009, 1, 12),
  "A09-02": datetime.datetime(2009, 2, 6),
  "A09-03": datetime.datetime(2009, 7, 7),
  "A09-04": datetime.datetime(2009, 6, 30),
  "A09-05": datetime.datetime(2009, 7, 20),
  "A09-06": datetime.datetime(2009, 7, 28),
  "A09-07": datetime.datetime(2009, 8, 21),
  "A08-01": datetime.datetime(2007, 11, 16),
  "A08-02": datetime.datetime(2007, 11, 6),
  "A08-02A": datetime.datetime(2007, 12, 12),
  "A08-03": datetime.datetime(2008, 1, 23),
  "A08-04": datetime.datetime(2008, 3, 18),
  "A08-05": datetime.datetime(2008, 8, 29),
  "A08-06": datetime.datetime(2008, 9, 10),
  "A08-07": datetime.datetime(2008, 9, 22),
  "A08-08": datetime.datetime(2008, 9, 22),
  "A07-01": datetime.datetime(2006, 11, 13),
  "OR07-01": datetime.datetime(2007, 1, 19),
  "A07-02": datetime.datetime(2007, 5, 4),
  "OR07-02": datetime.datetime(2007, 6, 29),
  "A06-01": datetime.datetime(2006, 3, 30),
  "OR06-01": datetime.datetime(2006, 8, 22),
  "A06-02": datetime.datetime(2006, 8, 1),
  "A06-04": datetime.datetime(2006, 10, 2),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  doc = utils.beautifulsoup_from_url(AUDIT_REPORTS_URL)
  results = doc.select("table tr")
  if not results:
    raise inspector.NoReportsFoundError("Federal Maritime Commission (audits)")
  for result in results:
    if result.th:
      # Skip the header row
      continue
    report = report_from(result, AUDIT_REPORTS_URL, report_type='audit', year_range=year_range)
    if report:
      inspector.save_report(report)

  # Pull historical audits
  audit_year_links = doc.select("div.col-2-3 ul li a")
  for year_link in audit_year_links:
    audit_year_url = urljoin(AUDIT_REPORTS_URL, year_link.get('href'))
    doc = utils.beautifulsoup_from_url(audit_year_url)
    results = doc.select("table tr")
    if not results:
      # Grab results other than first and last (header and extra links)
      results = doc.select("div.col-2-2 ul")[1:-1]
    if not results:
      raise inspector.NoReportsFoundError("Federal Maritime Commission (%s)" % audit_year_url)
    for result in results:
      if result.th:
        # Skip the header row
        continue
      report = report_from(result, AUDIT_REPORTS_URL, report_type='audit', year_range=year_range)
      if report:
        inspector.save_report(report)

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
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

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  if not published_on:
    try:
      published_on_text = title.split("-")[-1].strip()
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except ValueError:
      pass

  if not published_on:
    admin.log_no_date("fmc", report_id, title, report_url)
    return

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
  return report

utils.run(run) if (__name__ == "__main__") else None
