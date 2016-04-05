#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin, unquote

from utils import utils, inspector

# http://www.eac.gov/inspector_general/
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

CONGRESSIONAL_TESTIMONY_URL = "http://www.eac.gov/inspector_general/congressional_testimony.aspx"
HAVA_AUDITS_URL = "http://www.eac.gov/inspector_general/hava_funds_audits.aspx"
EAC_AUDITS_URL = "http://www.eac.gov/inspector_general/eac_audits_and_evaluations.aspx"
CONGRESSIONAL_REPORTS_URL = "http://www.eac.gov/inspector_general/congressional_reports.aspx"
INVESTIGATIONS_URL = "http://www.eac.gov/inspector_general/investigation_reports.aspx"
PEER_REVIEWS_URL = "http://www.eac.gov/inspector_general/peer_review_reports.aspx"

REPORT_URLS = [
  ("testimony", CONGRESSIONAL_TESTIMONY_URL),
  ("audit", HAVA_AUDITS_URL),
  ("audit", EAC_AUDITS_URL),
  ("congress", CONGRESSIONAL_REPORTS_URL),
  ("investigation", INVESTIGATIONS_URL),
  ("peer_review", PEER_REVIEWS_URL),
]

REPORT_PUBLISHED_MAP = {
  "U.S.-Election-Assistance-Commission's-Financial-Statements-for-Fiscal-Years-2015-and-2014": datetime.datetime(2015, 11, 12),
  "Final-Report---EAC-Compliance-with-FISMA-2015": datetime.datetime(2015, 11, 13),
  "2014-financial-audit-web": datetime.datetime(2014, 11, 12),
  "2014-FISMA-issued-report": datetime.datetime(2014, 11, 10),
  "2013-final-internet": datetime.datetime(2013, 12, 16),
  "issued-final-report-FISMA-20213": datetime.datetime(2013, 9, 19),
  "issued-final-report": datetime.datetime(2013, 9, 12),
  "2012-Final-Internet": datetime.datetime(2012, 11, 14),
  "Issued-EAC-Privacy-_FINAL_Report_Rev-5-8-13": datetime.datetime(2013, 5, 7),
  "FIMA-Internet-Version-2011": datetime.datetime(2011, 10, 5),
  "FISMA-Executive-Summary-2012": datetime.datetime(2012, 9, 17),
  "final-internet": datetime.datetime(2011, 11, 15),
  "Management-Letter---accessible-internet-version": datetime.datetime(2010, 11, 15),
  "AFR-2010-November-12-2010---FINAL": datetime.datetime(2010, 11, 15),
  "FISMA-2010---FINAL---Accessible": datetime.datetime(2010, 10, 27),
  "Evaluation-Report---Accessible": datetime.datetime(2010, 9, 28),
  "Assignment-No.-I-PA-EAC-01-09A": datetime.datetime(2009, 11, 13),
  "Assignment-No.-I-PA-EAC-01-09": datetime.datetime(2009, 11, 16),
  "Evaluation-of-Compliance-with-the-Requirements-of-the-Federal-Information-Security-Management-Act": datetime.datetime(2009, 10, 15),
  "Sweatshirts-Purchase-IG-Report": datetime.datetime(2009, 10, 1),
  "Management-Letter-Issues-Identified-During-the-Audit-of-the-EAC-Fiscal-Year-2008-Financial-Statements": datetime.datetime(2009, 3, 31),
  "Privacy-Report---Accessible-Version": datetime.datetime(2009, 3, 4),
  "EAC-Internet-Usage-Evaluation-report-FINAL---Accessible": datetime.datetime(2009, 2, 17),
  "Audit-of-the-EAC-Fiscal-Year-2008-Financial-Statements": datetime.datetime(2008, 11, 17),
  "FISMA_2008_-_Accessible": datetime.datetime(2008, 10, 31),
  "Assessment-of-EAC's-Program-and-Financial-Operations": datetime.datetime(2008, 2, 25),
  "final-fisma-report---accessible-version": datetime.datetime(2007, 9, 28),
  "FISMA-2006---accessible": datetime.datetime(2006, 10, 2),
  "Final-Report---Accessible": datetime.datetime(2007, 7, 5),
  "Redacted-Report-of-Investigation---ADA": datetime.datetime(2015, 8, 1),
  "Report-of-Investigation-Work-Environment-at-the-U.S.-Election-Assistance-Commission": datetime.datetime(2010, 3, 25),
  "EAC-Statement-Concerning-Inspector-General-Report": datetime.datetime(2010, 3, 26),
  "Report-of-Investigation---Preparation-of-the-Vote-Fraud-and-Voter-Intimidation-Report": datetime.datetime(2008, 3, 11),
  "Investigation-of-Allegations-of-Fraudulent-Certification-of-Election-Equipment-by-SysTest-Labs-Incorporated": datetime.datetime(2007, 12, 31),
  "209": datetime.datetime(2009, 6, 10),
  "2012-PeerReview-of-USElectionAssistanceCommision-by-FLRA-OIG": datetime.datetime(2012, 7, 31),
  "delaware-issued-2015": datetime.datetime(2015, 4, 6),
  "dc-issued-report": datetime.datetime(2015, 3, 24),
  "issued-idaho-2015": datetime.datetime(2015, 3, 12),
  "oklahoma-final-report-to-eac": datetime.datetime(2015, 2, 2),
  "maine-final-report---eac": datetime.datetime(2015, 2, 2),
  "colorado-issued": datetime.datetime(2014, 1, 28),
  "ND-issued-final": datetime.datetime(2013, 11, 6),
  "Ma-issued-report": datetime.datetime(2013, 11, 21),
  "vrirgin-islands-hava-issued": datetime.datetime(2013, 10, 31),
  "Ne-issued-final-report": datetime.datetime(2013, 9, 12),
  "mn-issued-final-report": datetime.datetime(2013, 9, 12),
  "il-issued-final-report": datetime.datetime(2013, 9, 12),
  "pa-issued-report": datetime.datetime(2013, 9, 12),
  "oh-issued-report": datetime.datetime(2013, 9, 12),
  "complete-nevada-report-internet-r": datetime.datetime(2011, 9, 30),
  "texas-complete-interent": datetime.datetime(2011, 8, 22),
  "arizona-final-internet": datetime.datetime(2011, 8, 22),
  "kansas-internet": datetime.datetime(2011, 8, 22),
  "nj-complete-final-acessible": datetime.datetime(2011, 6, 27),
  "iillinois-report---accessible": datetime.datetime(2011, 5, 6),
  "PA-report---accessible": datetime.datetime(2011, 5, 6),
  "utah-report---accessible": datetime.datetime(2011, 3, 31),
  "ny-final-report---accessible1": datetime.datetime(2011, 3, 7),
  "final-report-wv--accessible1": datetime.datetime(2011, 3, 7),
  "Hawaii-final-report---accessible": datetime.datetime(2011, 2, 4),
  "alabama-report---accessible": datetime.datetime(2011, 1, 28),
  "Louisiana-report---accessible": datetime.datetime(2011, 1, 28),
  "Project-Vote-Report-report---accessible": datetime.datetime(2010, 11, 8),
  "connecticut-report---accessible": datetime.datetime(2010, 9, 28),
  "Montana-report---accessible": datetime.datetime(2010, 9, 28),
  "mi-final-report---internet-version": datetime.datetime(2010, 4, 23),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-Tennessee-Secretary-of-State\u2019s-Division-of-Elections": datetime.datetime(2010, 4, 9),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-Arkansas-Secretary-of-State": datetime.datetime(2010, 2, 26),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-California's-Secretary-of-State": datetime.datetime(2009, 12, 14),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-State-of-Rhode-Island-and-Providence-Plantations": datetime.datetime(2009, 9, 30),
  "Administration-of-Payments-Recieved-Under-HAVA-by-Iowa-Secretary-of-State-2003-through-2008": datetime.datetime(2009, 9, 30),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-State-of-Oregon": datetime.datetime(2009, 6, 22),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-State-of-Florida": datetime.datetime(2008, 11, 17),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-State-of-Washington-Secretary-of-State": datetime.datetime(2008, 11, 17),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-North-Carolina-State-Board-of-Elections": datetime.datetime(2008, 10, 31),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-Minnesota-Secretary-of-State": datetime.datetime(2008, 7, 14),
  "Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-New-Mexico-Secretary-of-State": datetime.datetime(2008, 5, 27),
  "Final-Audit-Report-\u2013-Administration-of-Payments-Received-Under-the-Help-America-Vote-Act-by-the-State-of-Missouri-Secretary-of-State": datetime.datetime(2007, 10, 26),
  "Assignment-Number-E-HP-WY-03-07": datetime.datetime(2008, 1, 23),
  "Assignment-Number-E-HP-KY-02-07": datetime.datetime(2007, 8, 24),
  "Assignment-Number-E-HP-MD-08-06": datetime.datetime(2007, 6, 5),
  "Assignment-Number-E-HP-OH-09-06": datetime.datetime(2007, 5, 3),
  "Assignment-Number-E-HP-VA-12-06": datetime.datetime(2007, 5, 17),
  "Assignment-Number-E-HP-IN-13-06": datetime.datetime(2007, 5, 11),
  "Assignment-No.-E-HP-PA-10-06": datetime.datetime(2007, 1, 10),
  "Assignment-No.-E-HP-SC-11-06": datetime.datetime(2007, 1, 11),
  "Assignment-No.E-HP-IL-07-06": datetime.datetime(2006, 10, 18),
  "Assignment-No.-E-HP-TX-06-06": datetime.datetime(2006, 10, 18),
  "Assignment-No.-E-HP-NJ-04-06": datetime.datetime(2006, 9, 18),
  "Assignment-no.-E-HP-GA-05-06": datetime.datetime(2006, 7, 12),
  "Assignment-No.E-HP-CA-01-06": datetime.datetime(2005, 12, 19),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("div.mainRegion p a")
    if not results:
      raise inspector.NoReportsFoundError("EAC (%s)" % url)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def clean_text(text):
  return text.replace('\xa0', ' ').strip()

def report_from(result, landing_url, report_type, year_range):
  report_url = urljoin(landing_url, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  report_id = unquote(report_id)
  report_id = "-".join(report_id.split())

  title = clean_text(result.text)

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  if not published_on:
    try:
      published_on_text = "-".join(re.findall('(\w+) (\d+), (\d{4})', title)[-1])
      published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')
    except IndexError:
      pass
  if not published_on:
    try:
      published_on_text = "-".join(re.search('(\d+) (\w+) (\d{4})', title).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%d-%B-%Y')
    except (AttributeError, ValueError):
      pass
  if not published_on:
    inspector.log_no_date(report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'eac',
    'inspector_url': 'http://www.eac.gov/inspector_general/',
    'agency': 'eac',
    'agency_name': 'Election Assistance Commission',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
