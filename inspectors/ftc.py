#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector

# https://www.ftc.gov/about-ftc/office-inspector-general
archive = 1990

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add published dates for reports

AUDIT_REPORTS_URL = "https://www.ftc.gov/about-ftc/office-inspector-general/oig-reading-room/oig-audit-reports"
SEMIANNUAL_REPORTS_URL = "https://www.ftc.gov/about-ftc/office-inspector-general/oig-reading-room/semi-annual-reports-congress"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
}

REPORT_PUBLISHED_MAP = {
  "oig-rpt-compliance-_ipera-fy2015": datetime.datetime(2016, 5, 13),
  "ftcfismarepor2015": datetime.datetime(2016, 2, 29),
  "ftcmgmtltrfy2015": datetime.datetime(2016, 1, 8),
  "2016_oig_ocio_report": datetime.datetime(2015, 12, 16),
  "151208oig-mgmtchallenges": datetime.datetime(2015, 10, 15),
  "financialstmtauditfy2015.pdf": datetime.datetime(2015, 11, 16),
  "150630beevaluation": datetime.datetime(2015, 6, 30),
  "150526fismareport": datetime.datetime(2015, 5, 1),
  "150515iperareport": datetime.datetime(2015, 5, 13),
  "2014ftcmanagementletter": datetime.datetime(2015, 3, 18),
  "financialstmtauditfy2014": datetime.datetime(2014, 11, 17),
  "2015proposaloigoversight": datetime.datetime(2014, 11, 6),
  "141014oig-mgmtchallenges": datetime.datetime(2014, 10, 14),
  "2015evaluationftcbcpreport": datetime.datetime(2014, 10, 2),
  "2013parreportletter": datetime.datetime(2014, 5, 28),
  "ar2014recoveryact": datetime.datetime(2014, 4, 9),
  "ar14002": datetime.datetime(2014, 2, 1),
  "2013parreport": datetime.datetime(2013, 12, 16),
  "2012parreport": datetime.datetime(2012, 11, 15),
  "ar-12-002": datetime.datetime(2013, 4, 1),
  "130315ipera-fy2012": datetime.datetime(2013, 3, 15),
  "ar12-002": datetime.datetime(2011, 12, 1),
  "2011parreport": datetime.datetime(2011, 11, 15),
  "110926warehouseauditreport": datetime.datetime(2011, 9, 26),
  "ma1116": datetime.datetime(2011, 7, 27),
  "oigsurveyhsrfees": datetime.datetime(2011, 7, 27),
  "ar11003": datetime.datetime(2011, 1, 28),
  "2010parreport": datetime.datetime(2010, 11, 12),
  "ar100003": datetime.datetime(2010, 8, 19),
  "2009parreport": datetime.datetime(2009, 11, 13),
  "ir09002": datetime.datetime(2009, 9, 29),
  "ar09001": datetime.datetime(2008, 11, 14),
  "ar08003": datetime.datetime(2008, 9, 25),
  "ar08002": datetime.datetime(2008, 9, 30),
  "ar08001a": datetime.datetime(2008, 1, 29),
  "2007financialstmt": datetime.datetime(2007, 11, 14),
  "ftcextpeer": datetime.datetime(2007, 12, 12),
  "ar0703crc": datetime.datetime(2007, 7, 10),
  "ar07002final": datetime.datetime(2007, 3, 12),
  "ar0771a": datetime.datetime(2006, 12, 6),
  "2006financialstmt": datetime.datetime(2006, 11, 13),
  "ar0671": datetime.datetime(2006, 3, 29),
  "ar0670": datetime.datetime(2006, 2, 22),
  "ar05069a": datetime.datetime(2006, 1, 5),
  "ar05069": datetime.datetime(2005, 10, 28),
  "ar05068": datetime.datetime(2005, 9, 29),
  "ar05067": datetime.datetime(2005, 9, 30),
  "ar05066": datetime.datetime(2005, 5, 1),
  "ar0565": datetime.datetime(2005, 7, 29),
  "ar0563": datetime.datetime(2005, 1, 1),
  "ar0562a": datetime.datetime(2005, 1, 1),
  "ar0562": datetime.datetime(2004, 10, 29),
  "ar04059": datetime.datetime(2004, 2, 1),
  "ar04058": datetime.datetime(2004, 3, 31),
  "ar04057a": datetime.datetime(2004, 1, 1),
  "ar04057": datetime.datetime(2004, 1, 15),
  "ar04061": datetime.datetime(2004, 10, 6),
  "ar04060": datetime.datetime(2004, 1, 1),
  "ar03056": datetime.datetime(2003, 1, 1),
  "ar03055": datetime.datetime(2003, 1, 24),
  "fy2002fsamgmtltr": datetime.datetime(2003, 1, 1),
  "br02054": datetime.datetime(2002, 9, 24),
  "gizraudit": datetime.datetime(2002, 9, 16),
  "ar02052_0": datetime.datetime(2002, 2, 22),
  "011025grassley": datetime.datetime(2001, 10, 25),
  "cookies": datetime.datetime(2001, 4, 20),
  "wasa": datetime.datetime(2001, 2, 16),
  "ar01050a": datetime.datetime(2001, 1, 1),
  "ar01050_0": datetime.datetime(2001, 2, 21),
  "ar01049": datetime.datetime(2001, 1, 31),
  "ar00044": datetime.datetime(2000, 1, 31),
  "ar99041": datetime.datetime(1999, 3, 31),
  "independent-assessment-federal-trade-commission-implementation-federal-information-security": datetime.datetime(2010, 11, 1),
  "review-federal-trade-commission-implementation-federal-information-security-management-act": datetime.datetime(2009, 11, 1),
  "review-federal-trade-commission-implementation-federal-information-security-management-act-0": datetime.datetime(2008, 11, 1),
  "review-federal-information-security-management-act-fiscal-year-2007-non-public-report": datetime.datetime(2007, 11, 1),
  "review-federal-trade-commission-implementation-federal-information-security-management-act-1": datetime.datetime(2006, 11, 1),
  "gisra-security-evaluation-report-non-public-report": datetime.datetime(2002, 1, 1),
  "aging-analysis-redress-funds-held-account-memorandum-jodie-bernstein-director-bureau": datetime.datetime(1999, 11, 1),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for report_type, url in sorted(REPORT_URLS.items()):
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("li.views-row")
    if not results:
      raise inspector.NoReportsFoundError("FTC (%s)" % report_type)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  link = result.find("a")

  report_url = urljoin(landing_url, link.get('href').strip())
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  title = link.text

  file_type = None
  unreleased = False
  if "Non Public Report" in title.replace("-", " "):  # Normalize title for easier detection
    unreleased = True
    landing_url = report_url
    report_url = None
  elif not report_url.endswith(".pdf"):
    # A link to an html report
    file_type = "html"

  estimated_date = False
  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    if not os.path.splitext(report_filename)[1]:
      report_doc = utils.beautifulsoup_from_url(report_url)
      if report_doc:
        time_tag = report_doc.time
        if time_tag:
          date = report_doc.time["datetime"]
          published_on = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")

  if not published_on:
    if landing_url == SEMIANNUAL_REPORTS_URL:
      fy_match = re.match("Fiscal Year ([0-9]{4})", title)
      if fy_match:
        year = int(fy_match.group(1))
        if "(First Half)" in title:
          published_on = datetime.datetime(year, 3, 31)
          estimated_date = True
        elif "(Second Half)" in title:
          published_on = datetime.datetime(year, 9, 30)
          estimated_date = True

  if not published_on:
    inspector.log_no_date("ftc", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'ftc',
    'inspector_url': "https://www.ftc.gov/about-ftc/office-inspector-general",
    'agency': 'ftc',
    'agency_name': "Federal Trade Commission",
    'type': report_type,
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
  if file_type:
    report['file_type'] = file_type
  return report

utils.run(run) if (__name__ == "__main__") else None
