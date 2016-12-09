#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin, unquote

from utils import utils, inspector, admin

# https://www.flra.gov/components-offices/offices/office-inspector-general
archive = 1999

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/audit-reports"
INTERNAL_REVIEWS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/internal-reviews"
QA_REVIEWS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/quality-assurance-reviews"
SEMIANNUAL_REPORTS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/semiannual-reports"
PEER_REVIEWS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/peer-review-reports"

REPORT_URLS = [
  ("audit", AUDIT_REPORTS_URL),
  ("inspection", INTERNAL_REVIEWS_URL),
  ("inspection", QA_REVIEWS_URL),
  ("semiannual_report", SEMIANNUAL_REPORTS_URL),
  ("peer_review", PEER_REVIEWS_URL),
]

REPORT_ID_RE = re.compile("\(([A-Z]{2}-[0-9]{2}-[0-9]{2})\)|Report Number\\s+((?:[A-Z]{3}-)?[0-9]{2}-[0-9]{2})")

REPORT_PUBLISHED_MAP = {
  # Quality Assurance Reviews
  "ER-16-03": datetime.datetime(2016, 6, 22),
  "ER-15-03": datetime.datetime(2015, 6, 12),
  "ER-14-03": datetime.datetime(2014, 7, 2),
  "ER-13-03": datetime.datetime(2013, 8, 29),
  "ER-12-03": datetime.datetime(2012, 11, 2),

  # Peer Review Reports
  "14-04": datetime.datetime(2014, 9, 22),
  "11-04": datetime.datetime(2011, 6, 9),
  "01-08": datetime.datetime(2008, 9, 16),
  "QCR-05-01": datetime.datetime(2005, 4, 18),
  "QCR-02-01": datetime.datetime(2002, 4, 3),

  # Audit Reports
  "AR-17-01": datetime.datetime(2016, 11, 15),
  "AR-17-02": datetime.datetime(2016, 11, 16),
  "Final---AUC-260-Letter": datetime.datetime(2016, 11, 15),
  "AR-16-01": datetime.datetime(2015, 11, 16),
  "AR-16-02": datetime.datetime(2015, 12, 14),
  "AR-16-03": datetime.datetime(2016, 1, 20),
  "AR-16-04": datetime.datetime(2016, 5, 18),
  "2015-AU-C-260-Letter": datetime.datetime(2015, 12, 14),
  "AR-15-01": datetime.datetime(2014, 11, 14),
  "AR-15-02": datetime.datetime(2015, 1, 20),
  "AR-15-03": datetime.datetime(2014, 12, 2),
  "AR-15-04": datetime.datetime(2015, 1, 1),
  "2014-AU-C-260-Letter": datetime.datetime(2014, 11, 14),
  "AR-14-01": datetime.datetime(2013, 12, 6),
  "Transmittal-Letter-Dated-12-6-2013": datetime.datetime(2013, 12, 6),
  "AR-14-02": datetime.datetime(2013, 12, 18),
  "AR-14-03": datetime.datetime(2014, 2, 24),
  "Statement-on-114-Letter-Communication": datetime.datetime(2013, 12, 18),
  "AR-13-01": datetime.datetime(2012, 12, 15),
  "AR-13-02": datetime.datetime(2012, 12, 30),
  "2012-SAS-114-Letter": datetime.datetime(2012, 11, 30),
  "AR-12-01": datetime.datetime(2011, 11, 15),
  "AR-12-02": datetime.datetime(2011, 12, 28),
  "Statement-on-Auditing-Standards-No-114": datetime.datetime(2011, 12, 28),
  "AR-11-01": datetime.datetime(2010, 11, 15),
  "AR-11-02": datetime.datetime(2010, 9, 30),
  "FS-Audit-2009": datetime.datetime(2009, 11, 13),
  "FLRA-FY2009-Management-Letter": datetime.datetime(2009, 11, 15),
  "FS-Audit-2008": datetime.datetime(2009, 8, 14),
  "2009-Management-Letter-for-Fiscal-Year-2008": datetime.datetime(2009, 7, 9),
  "Financial-Statement-Audit-for-Fiscal-Year-2007": datetime.datetime(2008, 2, 8),
  "FS-Audit-2006": datetime.datetime(2007, 1, 1),
  "FS-Audit-2005": datetime.datetime(2005, 11, 14),
  "FS-Audit-2004": datetime.datetime(2004, 11, 12),
  "Audit-Report-FLRA-Security-Programs-(September-2004)---Non-Public-Report": datetime.datetime(2004, 9, 1),
  "Audit-Report-FLRA-Use-of-Government-Vehicles-Nov-20-2003": datetime.datetime(2003, 11, 20),

  # Internal Reviews
  "ER-17-02": datetime.datetime(2016, 12, 1),
  "final-data-ac-t-reportfina-loct-17-2016-er-17-03": datetime.datetime(2016, 10, 17),
  "ER-16-02": datetime.datetime(2016, 2, 3),
  "ER-15-02": datetime.datetime(2015, 2, 6),
  "ER-14-02": datetime.datetime(2014, 2, 11),
  "ER-13-02": datetime.datetime(2013, 1, 14),
  "ER-12-02": datetime.datetime(2012, 3, 12),
  "2009-Check-Out-Process-Report-for-FOIA": datetime.datetime(2009, 12, 7),
  "Internal-Review-of-Case-Intake-and-Publication-2009": datetime.datetime(2009, 10, 13),
  "2009-Internal-Review-of-Purchase-Cards": datetime.datetime(2009, 7, 13),
  "2009-Internal-Review-of-FSIP": datetime.datetime(2009, 3, 17),
  "2009-Internal-Review-of-IT": datetime.datetime(2009, 1, 26),
  "2009-Internal-Review-ALJ": datetime.datetime(2009, 3, 3),
  "Internal-Review-Human-Capital-Succession-Planning-Report": datetime.datetime(2009, 8, 21),
  "2009-Management-&-Employee-Survey-Report": datetime.datetime(2009, 6, 10),
  "Final-8-14-08-Admiinistration-Report": datetime.datetime(2008, 8, 14),
  "Report-of-Independent-Auditors-on-Internal-Controls-(2008)": datetime.datetime(2008, 2, 8),
  "Internal-Review-of-FLRA-Administrative-Instructions-Report-(2006)": datetime.datetime(2006, 11, 1),
  "Internal-Review-of-FLRA's-Alternative-Work-Schedule": datetime.datetime(2005, 1, 1),
  "Internal-Review-of-FLRA-Court-Reporting-Procurement-(December,-2004)-Executive-Summary": datetime.datetime(2004, 12, 1),
  "Internal-Review-of-FLRA's-Occupational-Safety-and-Health-Program": datetime.datetime(2004, 12, 9),
  "Internal-Review-of-FLRA's-Human-Capital-Progress-Assessment-Followup-on-2000-and-May-2,-2003": datetime.datetime(2003, 5, 2),
  "FLRA's-FY-2002-Use-of-Government-Credit-Card": datetime.datetime(2002, 11, 5),
  "Fair-Act-Evaluation": datetime.datetime(2002, 1, 1),
  "Evaluation-of-the-FLRA-FY-99-Annual-Performance-Plan-Submission": datetime.datetime(2000, 11, 1),
  "External-Affairs-Function-Internal-Review-(Report-No.-00-02)": datetime.datetime(2000, 5, 1),
  "Human-Capital-Investment": datetime.datetime(2000, 1, 1),
  "Management-Letter-dated-April-14,-1999": datetime.datetime(1999, 4, 14),
  "Evaluation-of-the-FLRA-FY99-Annual-Performance-Plan-Submission": datetime.datetime(2000, 11, 1),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("section#content ul li")
    if not results:
      raise inspector.NoReportsFoundError("Federal Labor Relations Authority (%s)" % report_type)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  title = result.text.strip()

  if 'Non-Public Report' in title:
    unreleased = True
    report_url = None
    report_id = "-".join(unquote(title).split())
    report_id = report_id.replace(":", "")
  else:
    unreleased = False
    link = result.find("a")
    if not link:
      return None
    # Some reports have incorrect relative paths
    relative_report_url = link.get('href').replace("../", "")
    report_url = urljoin(landing_url, relative_report_url)
    report_id_match = REPORT_ID_RE.search(title)
    if report_id_match:
      report_id = report_id_match.group(1) or report_id_match.group(2)
    else:
      report_filename = report_url.split("/")[-1]
      report_id, _ = os.path.splitext(report_filename)
      report_id = "-".join(unquote(report_id).split())

  estimated_date = False
  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  if not published_on:
    try:
      published_on = datetime.datetime.strptime(title, '%B %Y')
    except ValueError:
      pass

  if not published_on:
    if "Non-Public Report" in title:
      year_match = re.search("\\(([0-9]{4})\\)", title)
      if year_match:
        year = int(year_match.group(1))
        published_on = datetime.datetime(year, 1, 1)
        estimated_date = True

  if not published_on:
    admin.log_no_date("flra", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'flra',
    'inspector_url': 'https://www.flra.gov/components-offices/offices/office-inspector-general',
    'agency': 'flra',
    'agency_name': 'Federal Labor Relations Authority',
    'file_type': 'pdf',
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
  return report

utils.run(run) if (__name__ == "__main__") else None
