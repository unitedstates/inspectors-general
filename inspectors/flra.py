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

AUDIT_REPORTS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/reports-and-correspondence"
INTERNAL_REVIEWS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/internal-reviews"
QA_REVIEWS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/quality-assurance-reviews"
SEMIANNUAL_REPORTS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/semiannual-reports-congress"
PEER_REVIEWS_URL = "https://www.flra.gov/components-offices/offices/office-inspector-general/peer-review-reports"

REPORT_URLS = [
  ("audit", AUDIT_REPORTS_URL),
  ("inspection", INTERNAL_REVIEWS_URL),
  ("inspection", QA_REVIEWS_URL),
  ("semiannual_report", SEMIANNUAL_REPORTS_URL),
  ("peer_review", PEER_REVIEWS_URL),
]

REPORT_ID_RE_1 = re.compile("\\(([A-Z]{2}-[0-9]{2}-[0-9]{2}[A-Z]?)\\)|Report (?:Number|No\\.)\\s+((?:[A-Z]{2,3}-)?[0-9]{2}-[0-9]{2}[A-Z]?)")
REPORT_ID_RE_2 = re.compile("^((?:[A-Z]{2,3}-)?[0-9]{2}-[0-9]{2}[A-Z]?)")
REPORT_ID_RE_3 = re.compile("^OIG-[0-9]{4}-[0-9]{2}$")

REPORT_PUBLISHED_MAP = {
  # Peer Review Reports
  "OIG-2017-10": datetime.datetime(2017, 6, 30),
  "14-04": datetime.datetime(2014, 9, 22),
  "11-04": datetime.datetime(2011, 6, 9),
  "01-08": datetime.datetime(2008, 9, 16),
  "QCR-05-01": datetime.datetime(2005, 4, 18),
  "QCR-02-01": datetime.datetime(2002, 4, 3),

  # Audit Reports
  "AR-17-01": datetime.datetime(2016, 11, 15),
  "AR-17-02": datetime.datetime(2016, 11, 16),
  "AR-17-03": datetime.datetime(2016, 11, 15),
  "AR-17-04": datetime.datetime(2017, 1, 13),
  "ER-17-01": datetime.datetime(2017, 1, 1),
  "ER-17-02": datetime.datetime(2016, 12, 1),
  "ER-17-03": datetime.datetime(2016, 10, 17),
  "ER-17-04": datetime.datetime(2017, 5, 1),
  "ER-17-05": datetime.datetime(2017, 5, 9),
  "MC-17-01": datetime.datetime(2016, 11, 2),
  "AR-16-01": datetime.datetime(2015, 11, 16),
  "AR-16-02": datetime.datetime(2015, 12, 14),
  "AR-16-03": datetime.datetime(2016, 1, 20),
  "AR-16-04": datetime.datetime(2016, 5, 18),
  "AR-16-05": datetime.datetime(2015, 12, 14),
  "ER-16-01": datetime.datetime(2016, 1, 1),
  "ER-16-02": datetime.datetime(2016, 2, 3),
  "ER-16-03": datetime.datetime(2016, 6, 22),
  "MC-16-01": datetime.datetime(2015, 10, 22),
  "AR-15-01": datetime.datetime(2014, 11, 14),
  "AR-15-02": datetime.datetime(2015, 1, 20),
  "AR-15-03": datetime.datetime(2014, 12, 2),
  "AR-15-04": datetime.datetime(2015, 1, 1),
  "AR-15-05": datetime.datetime(2014, 11, 14),
  "ER-15-01": datetime.datetime(2015, 1, 1),
  "ER-15-02": datetime.datetime(2015, 2, 6),
  "ER-15-03": datetime.datetime(2015, 6, 12),
  "MC-15-01": datetime.datetime(2014, 10, 23),
  "AR-14-01": datetime.datetime(2013, 12, 6),
  "AR-14-01A": datetime.datetime(2013, 12, 6),
  "AR-14-02": datetime.datetime(2013, 12, 18),
  "AR-14-03": datetime.datetime(2014, 2, 24),
  "AR-14-04": datetime.datetime(2013, 12, 18),
  "ER-14-01": datetime.datetime(2014, 1, 1),
  "ER-14-02": datetime.datetime(2014, 2, 11),
  "ER-14-03": datetime.datetime(2014, 7, 2),
  "MC-14-01": datetime.datetime(2014, 10, 23),
  "AR-13-01": datetime.datetime(2012, 12, 15),
  "AR-13-02": datetime.datetime(2012, 12, 30),
  "AR-13-03": datetime.datetime(2012, 11, 30),
  "ER-13-01": datetime.datetime(2013, 1, 1),
  "ER-13-02": datetime.datetime(2013, 1, 14),
  "ER-13-03": datetime.datetime(2013, 8, 29),
  "MC-13-01": datetime.datetime(2013, 10, 23),
  "AR-12-01": datetime.datetime(2011, 11, 15),
  "AR-12-02": datetime.datetime(2011, 12, 28),
  "AR-12-03": datetime.datetime(2011, 12, 28),
  "ER-12-01": datetime.datetime(2012, 1, 1),
  "ER-12-02": datetime.datetime(2012, 3, 12),
  "ER-12-03": datetime.datetime(2012, 11, 2),
  "MC-12-01": datetime.datetime(2011, 10, 12),
  "AR-11-01": datetime.datetime(2010, 11, 15),
  "AR-11-02": datetime.datetime(2010, 9, 30),
  "ER-11-01": datetime.datetime(2011, 1, 1),
  "MC-11-01": datetime.datetime(2010, 10, 1),
  "AR-10-01": datetime.datetime(2009, 11, 13),
  "AR-10-02": datetime.datetime(2009, 11, 15),
  "ER-10-01": datetime.datetime(2010, 1, 1),
  "ER-10-02": datetime.datetime(2009, 10, 13),
  "MC-10-01": datetime.datetime(2009, 10, 1),
  "AR-09-01": datetime.datetime(2009, 8, 14),
  "AR-09-02": datetime.datetime(2009, 7, 9),
  "ER-09-01": datetime.datetime(2008, 9, 1),
  "ER-09-02": datetime.datetime(2009, 7, 13),
  "ER-09-03": datetime.datetime(2009, 3, 17),
  "ER-09-04": datetime.datetime(2009, 1, 26),
  "ER-09-05": datetime.datetime(2009, 3, 3),
  "ER-09-06": datetime.datetime(2009, 8, 21),
  "ER-09-07": datetime.datetime(2009, 6, 10),
  "ER-09-08": datetime.datetime(2009, 7, 22),
  "MC-09-01": datetime.datetime(2009, 3, 23),
  "AR-08-01": datetime.datetime(2008, 2, 8),
  "AR-08-02": datetime.datetime(2008, 2, 8),
  "ER-08-01": datetime.datetime(2008, 9, 26),
  "ER-08-02": datetime.datetime(2008, 8, 14),
  "MC-08-01": datetime.datetime(2007, 10, 11),
  "ER-07-01": datetime.datetime(2007, 9, 12),
  "ER-07-02": datetime.datetime(2007, 9, 1),
  "ER-07-03": datetime.datetime(2006, 11, 1),
  "AR-06-01": datetime.datetime(2005, 11, 14),
  "ER-06-01": datetime.datetime(2006, 9, 1),
  "AR-05-01": datetime.datetime(2004, 11, 12),
  "ER-05-01": datetime.datetime(2005, 8, 19),
  "AR-04-01": datetime.datetime(2003, 11, 30),
  "ER-04-01": datetime.datetime(2004, 9, 1),
  "ER-04-02": datetime.datetime(2004, 12, 1),
  "ER-03-01": datetime.datetime(2003, 9, 1),
  "ER-03-02": datetime.datetime(2003, 9, 1),
  "ER-03-03": datetime.datetime(2003, 5, 2),
  "ER-03-04": datetime.datetime(2002, 11, 5),
  "ER-02-01": datetime.datetime(2002, 9, 11),
  "ER-01-01": datetime.datetime(2000, 11, 1),
  "ER-00-01": datetime.datetime(2000, 1, 1),
  "ER-00-02": datetime.datetime(2000, 5, 1),
  "ER-99-01": datetime.datetime(1999, 4, 14),
  "Financial-Statement-Audit-for-Fiscal-Year-2007": datetime.datetime(2008, 2, 8),
  "FS-Audit-2006": datetime.datetime(2007, 1, 1),
  "FS-Audit-2005": datetime.datetime(2005, 11, 14),
  "FS-Audit-2004": datetime.datetime(2004, 11, 12),
  "Financial-Statement-Audit-for-Fiscal-Year-2004": datetime.datetime(2004, 11, 12),
  "Audit-Report-FLRA-Security-Programs-(September-2004)---Non-Public-Report": datetime.datetime(2004, 9, 1),
  "Audit-Report-FLRA-Use-of-Government-Vehicles-Nov-20-2003": datetime.datetime(2003, 11, 20),
  "Audit-Report-FLRA-Use-of-Government-Vehicles-(November-20,-2003)": datetime.datetime(2003, 11, 20),

  # Internal Reviews
  "2009-Check-Out-Process-Report-for-FOIA": datetime.datetime(2009, 12, 7),
  "Internal-Review-of-Case-Intake-and-Publication-2009": datetime.datetime(2009, 10, 13),
  "Federal-Labor-Relations-Authority-Inspector-General-FISMA-Evaluation-(2009)---Non-Public-Report": datetime.datetime(2009, 1, 1),
  "2009-Internal-Review-of-Purchase-Cards": datetime.datetime(2009, 7, 13),
  "2009-Internal-Review-of-FSIP": datetime.datetime(2009, 3, 17),
  "2009-Internal-Review-of-IT": datetime.datetime(2009, 1, 26),
  "2009-Internal-Review-ALJ": datetime.datetime(2009, 3, 3),
  "Internal-Review-Human-Capital-Succession-Planning-Report": datetime.datetime(2009, 8, 21),
  "2009-Management-&-Employee-Survey-Report": datetime.datetime(2009, 6, 10),
  "Federal-Labor-Relations-Authority-Inspector-General-FISMA-Evaluation-(2008)---Non-Public-Report": datetime.datetime(2008, 1, 1),
  "Final-8-14-08-Admiinistration-Report": datetime.datetime(2008, 8, 14),
  "Report-of-Independent-Auditors-on-Internal-Controls-(2008)": datetime.datetime(2008, 2, 8),
  "FLRA-Management-FISMA-Survey-Results-(2007)---Non-Public-Report": datetime.datetime(2007, 1, 1),
  "Internal-Review-of-FLRA-Administrative-Instructions-Report-(2006)": datetime.datetime(2006, 11, 1),
  "Internal-Review-of-FLRA's-Alternative-Work-Schedule": datetime.datetime(2005, 1, 1),
  "Internal-Review-of-FLRA-Court-Reporting-Procurement-(December,-2004)-Executive-Summary": datetime.datetime(2004, 12, 1),
  "Internal-Review-of-FLRA's-Occupational-Safety-and-Health-Program": datetime.datetime(2004, 12, 9),
  "Internal-Review-of-FLRA's-Human-Capital-Progress-Assessment-Followup-on-2000-and-May-2,-2003": datetime.datetime(2003, 5, 2),
  "FLRA's-FY-2002-Use-of-Government-Credit-Card": datetime.datetime(2002, 11, 5),
  "Fair-Act-Evaluation": datetime.datetime(2002, 1, 1),
  "Evaluation-of-the-FLRA-FY-99-Annual-Performance-Plan-Submission": datetime.datetime(2000, 11, 1),
  "00-02": datetime.datetime(2000, 5, 1),
  "00-01": datetime.datetime(2000, 1, 1),
  "Management-Letter-dated-April-14,-1999": datetime.datetime(1999, 4, 14),
  "Evaluation-of-the-FLRA-FY99-Annual-Performance-Plan-Submission": datetime.datetime(2000, 11, 1),
}


def run(options):
  year_range = inspector.year_range(options, archive)
  keys = set()

  # Pull the reports
  for report_type, url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("section#content ul li")
    if results:
      for result in results:
        report = report_from_list(result, url, report_type, year_range)
        if report:
          if report["url"]:
            key = (report["report_id"], unquote(report["url"]))
          else:
            key = (report["report_id"], report["url"])
          if key not in keys:
            inspector.save_report(report)
            keys.add(key)
    else:
      results = doc.select("section#content p")
      if not results:
        raise inspector.NoReportsFoundError("Federal Labor Relations Authority (%s)" % report_type)
      for result in results:
        report = report_from_paragraph(result, url, report_type, year_range)
        if report:
          key = (report["report_id"], report["url"])
          if key not in keys:
            inspector.save_report(report)
            keys.add(key)


def report_from_paragraph(result, landing_url, report_type, year_range):
  missing = False
  text = result.text.strip()
  if not text:
    return
  if "The Office of Inspector General conducts independent\u00a0audits and reviews of" in text:
    return
  if "Office of\u00a0Inspectors General (OIG)\u00a0performing audits\u00a0are required to perform" in text:
    return
  if "Report\u00a0No." in text and "Report Title" in text:
    return
  if "Report\u00a0 No." in text and "Report Title" in text:
    return
  if "Report No." in text and "Report Title" in text:
    return
  if text == "Report Title":
    return

  chunks = text.split("\u00a0", maxsplit=1)
  report_id = None
  unreleased = False
  if len(chunks) >= 2:
    title = chunks[1].strip()
    report_id_match = REPORT_ID_RE_2.match(chunks[0].strip())
    if report_id_match:
      report_id = report_id_match.group(1)
    report_id_match = REPORT_ID_RE_3.match(chunks[0].strip())
    if report_id_match:
      report_id = report_id_match.group(0)
  if not report_id and result.a:
    title = text
    report_filename = result.a.get("href").split("/")[-1]
    report_id, _ = os.path.splitext(report_filename)
    report_id = "-".join(unquote(report_id).split())
  if not report_id:
    title = result.text.strip()
    report_id = "-".join(title.split())
    report_id = report_id.replace(":", "")

  if ('Non-Public Report' in title or
          'Non -Public Report' in title or
          'Non Public Report' in title):
    unreleased = True

  if result.a:
    link = result.a
    if not link:
      return None
    # Some reports have incorrect relative paths
    relative_report_url = link.get('href').replace("../", "")
    report_url = urljoin(landing_url, relative_report_url)
  else:
    report_url = None

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
    admin.log_no_date("flra", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  if published_on.year <= 2011 and not unreleased and not report_url:
    # Some older reports aren't posted
    unreleased = True
    missing = True

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
  if missing:
    report['missing'] = missing
  return report


def report_from_list(result, landing_url, report_type, year_range):
  missing = False
  title = re.sub("\\s+", " ", inspector.sanitize(result.text))

  report_id = None
  report_id_match = REPORT_ID_RE_1.search(title)
  if report_id_match:
    report_id = report_id_match.group(1) or report_id_match.group(2)

  if 'Non-Public Report' in title:
    unreleased = True
    report_url = None
    if report_id in ("ER-11-01", "ER-12-01", "ER-13-01", "ER-14-01",
                     "ER-15-01", "ER-16-01", "ER-17-01"):
      # These reports are listed in two places, once with a PDF, once without
      return
    if not report_id:
      report_id = "-".join(title.split())
      report_id = report_id.replace(":", "")
  else:
    unreleased = False
    link = result.find("a")
    if not link:
      return None
    # Some reports have incorrect relative paths
    relative_report_url = link.get('href').replace("../", "")
    report_url = urljoin(landing_url, relative_report_url)
    if report_url == "https://www.flra.gov/system/files/webfm/Inspector%20General/FLRA%20IPERA%20Compliance%202011.pdf" and report_id == "ER-12-02":
      report_url = "https://www.flra.gov/system/files/webfm/Inspector%20General/IPERA%20March%202012.pdf"
    if not report_id:
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
    admin.log_no_date("flra", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  if published_on.year <= 2011 and not unreleased and not report_url:
    # Some older reports aren't posted
    unreleased = True
    missing = True

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
  if missing:
    report['missing'] = missing
  return report

utils.run(run) if (__name__ == "__main__") else None
