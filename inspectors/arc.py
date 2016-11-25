#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector, admin

# http://www.arc.gov/oig
archive = 2003

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.arc.gov/about/OfficeofInspectorGeneralAuditandInspectionReports.asp"
SEMIANNUAL_REPORTS_URL = "http://www.arc.gov/about/OfficeofinspectorGeneralSemiannualReports.asp"
PEER_REVIEWS_URL = "http://www.arc.gov/about/OfficeofInspectorGeneralExternalPeerReviewReports.asp"

REPORT_TYPES = {
  "audit": AUDIT_REPORTS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "peer_review": PEER_REVIEWS_URL,
}

REPORT_PUBLISHED_MAP = {
  "peer_review_2007": datetime.datetime(2007, 2, 20),
  "PeerReviewReport2011": datetime.datetime(2011, 3, 18),

  "Report08-01ReviewofHealthProvJ1VisaKY": datetime.datetime(2007, 10, 29),
  "Report08-02ReviewofHealthProvJ1VisaOH": datetime.datetime(2007, 10, 31),
  "Report08-03ReviewofHealthProvJ1VisaTN": datetime.datetime(2008, 1, 31),
  "Report08-04ReviewofHealthProvJ1VisaNY": datetime.datetime(2008, 1, 31),
  "Report08-05ReviewofHealthProvJ1VisaMS": datetime.datetime(2008, 1, 31),
  "Report08-06ReviewofHealthProvJ1VisaAL": datetime.datetime(2008, 2, 19),
  "Report08-07-AL-14720": datetime.datetime(2008, 4, 3),
  "Report08-08-AL-14835-0-1": datetime.datetime(2008, 4, 3),
  "Report08-09ARCGrantManagementSystemAudit": datetime.datetime(2008, 4, 11),
  "Report08-10-TN-14941-04": datetime.datetime(2008, 4, 21),
  "Report08-11-KY-14118": datetime.datetime(2008, 6, 23),
  "Report08-12-KY-14974": datetime.datetime(2008, 6, 23),
  "Report08-13-KY-15056": datetime.datetime(2008, 6, 23),
  "Report08-14-FY2007FinancialStatementAudit": datetime.datetime(2008, 7, 24),
  "Report09-01-FY2007and2008FinancialStatementAudits": datetime.datetime(2009, 6, 4),
  "Report09-02_ReviewOfUnivALChildDevCtr-CO-14150-I-302": datetime.datetime(2009, 6, 12),
  "Report09-03GrantManagementInspectionReport": datetime.datetime(2009, 8, 3),
  "Report09-04ARCInternalControlPerformanceAudit": datetime.datetime(2009, 9, 24),
  "Report10-01-WV-14468-03": datetime.datetime(2010, 2, 16),
  "Report10-02-WV-14468-C1-04": datetime.datetime(2010, 2, 16),
  "Report10-03-WV-14468-C2-05": datetime.datetime(2010, 2, 16),
  "Report10-04-WV-14468-C3-06": datetime.datetime(2010, 2, 16),
  "Report10-05-FY2008andFY2009Audits": datetime.datetime(2010, 6, 8),
  "Report10-06-GrantManagementCompliance": datetime.datetime(2010, 7, 2),
  "Report11-01-CO-15789-07": datetime.datetime(2010, 12, 9),
  "Report11-02-KY-15648-07": datetime.datetime(2011, 3, 7),
  "Report11-03-FY2010-Audit": datetime.datetime(2011, 3, 28),
  "Report11-04-CO-15528-06": datetime.datetime(2011, 6, 15),
  "Report11-05OpenBasicAgencyGrants": datetime.datetime(2011, 7, 21),
  "Report11-06OpenBasicAgencyGrants": datetime.datetime(2011, 7, 21),
  "Report11-07ARCPerformanceMeasures": datetime.datetime(2011, 7, 29),
  "Report11-08-WV-15973-08": datetime.datetime(2011, 9, 27),
  "Report11-09-J-1VisaWaiverPrograminAlabama": datetime.datetime(2011, 9, 27),
  "Report12-01FiscalYear2011FinancialStatementAudit": datetime.datetime(2011, 11, 22),
  "Report12-02-NY-17093": datetime.datetime(2011, 11, 22),
  "Report12-03-FollowUpBasicAgencyGrants": datetime.datetime(2011, 12, 13),
  "Report12-04-MD-15597": datetime.datetime(2012, 2, 24),
  "Report12-05-GrantProcessingTimeliness": datetime.datetime(2012, 3, 13),
  "Report12-06-OpenARCAdminGrantsFundBalances": datetime.datetime(2012, 3, 12),
  "Report12-07-NY-2337": datetime.datetime(2012, 2, 28),
  "Report12-08-MD-15338": datetime.datetime(2012, 2, 17),
  "Report12-09-NY-16246": datetime.datetime(2012, 2, 23),
  "Report12-10-SurveyGrantControls": datetime.datetime(2012, 3, 13),
  "Report12-11-VA-16353": datetime.datetime(2012, 5, 29),
  "Report12-12-AL-16709-302-10": datetime.datetime(2012, 5, 11),
  "Report12-13-AL-16379-302-09": datetime.datetime(2012, 5, 25),
  "Report12-14-NC-15448": datetime.datetime(2012, 5, 8),
  "Report12-15-GA-15187": datetime.datetime(2012, 7, 2),
  "Report12-16-SC-15834-302-08": datetime.datetime(2012, 5, 1),
  "Report12-17-SC-16352-302-09": datetime.datetime(2012, 8, 17),
  "Report12-18-TN-15808": datetime.datetime(2012, 6, 19),
  "Report12-19-KY-16080": datetime.datetime(2012, 8, 15),
  "Report12-20-KY-16060": datetime.datetime(2012, 8, 15),
  "Report12-21-CO-13956": datetime.datetime(2012, 9, 25),
  "Report12-22-OH-7781-C31-302-10": datetime.datetime(2012, 9, 30),
  "Report12-23-WV-7762": datetime.datetime(2012, 9, 25),
  "Report12-24-PA-15726": datetime.datetime(2012, 9, 26),
  "Report12-25-OH-10533-C17-11": datetime.datetime(2012, 9, 30),
  "Report12-26-OpenChildAgencyGrants": datetime.datetime(2012, 9, 30),
  "Report12-27-OpenARCAdministeredGrants": datetime.datetime(2012, 9, 30),
  "Report13-01FiscalYear2012FinancialStatementAudit": datetime.datetime(2012, 12, 5),
  "Report13-02-VA-7782-C29-11": datetime.datetime(2013, 1, 29),
  "Report13-03-MS-16115": datetime.datetime(2012, 12, 14),
  "Report13-04-MS-16778": datetime.datetime(2012, 12, 14),
  "Report13-05-MD-0703A-C42": datetime.datetime(2013, 1, 29),
  "Report13-06-AL-14991-C4-2011": datetime.datetime(2013, 1, 31),
  "Report13-07-AL-15842-C3-2011": datetime.datetime(2013, 4, 25),
  "Report13-08-KY-15959": datetime.datetime(2013, 1, 25),
  "Report13-09-KY-16403": datetime.datetime(2013, 1, 25),
  "Report13-10-TN-7783": datetime.datetime(2013, 3, 29),
  "Report13-11-TN-15759": datetime.datetime(2013, 3, 29),
  "Report13-12-TN-710-A": datetime.datetime(2013, 5, 30),
  "Report13-13-GA-7769-C31": datetime.datetime(2013, 3, 2),
  "Report13-13A-GA-701G-C1": datetime.datetime(2013, 4, 25),
  "Report13-14-WV-2730": datetime.datetime(2012, 11, 28),
  "Report13-14A-GA-701G-C1andC1-R1": datetime.datetime(2013, 4, 25),
  "Report13-15-KY-17088": datetime.datetime(2013, 8, 16),
  "Report13-16-KY-17067-302-11": datetime.datetime(2013, 4, 25),
  "Report13-17-ARCGrantAdminProcess": datetime.datetime(2013, 3, 31),
  "Report13-18OlderOpenBasicChildAgencyGrants": datetime.datetime(2013, 3, 31),
  "Report13-19OpenARCAdministeredGrants": datetime.datetime(2013, 3, 31),
  "Report13-20-TN-16661": datetime.datetime(2013, 5, 15),
  "Report13-21-PA-708G-C41+PA-8290-C30andC31": datetime.datetime(2013, 5, 17),
  "Report13-22-CO-16898": datetime.datetime(2013, 6, 19),
  "Report13-23-WV-16454": datetime.datetime(2013, 9, 4),
  "Report13-24-NC-7780-C32": datetime.datetime(2013, 9, 30),
  "Report13-25-MS-16376-C1-302-11": datetime.datetime(2013, 7, 31),
  "Report13-26-MS-7763-C31": datetime.datetime(2013, 8, 20),
  "Report13-27-SC-0709-C45": datetime.datetime(2013, 6, 6),
  "Report13-28-AL-16572": datetime.datetime(2013, 9, 30),
  "Report13-29-WV-17149": datetime.datetime(2013, 7, 12),
  "Report13-30-NY-2324-C41": datetime.datetime(2013, 8, 16),
  "Report13-31-OH-17152": datetime.datetime(2013, 8, 27),
  "Report13-32-OH-707-B-C41": datetime.datetime(2013, 8, 7),
  "Report13-33-ConsolidatedTAGrants": datetime.datetime(2013, 9, 30),
  "Report13-34-NY-7776-C31andC32": datetime.datetime(2013, 8, 16),
  "Report13-35-ARCNetworkEvaluationReport": datetime.datetime(2013, 9, 27),
  "Report13-36-ARCSystemPatchingEvaluationReport": datetime.datetime(2013, 9, 27),
  "Report13-37-MD-17132": datetime.datetime(2013, 9, 30),
  "Report13-38-OlderOpenBasicChildAgencyGrants": datetime.datetime(2013, 9, 30),
  "Report13-39OlderOpenARCAdministeredGrants": datetime.datetime(2013, 9, 30),
  "Report13-40-StateAdministeredGrants": datetime.datetime(2013, 9, 30),
  "Report13-41-PerformanceMeasuresLDDandTAGrants": datetime.datetime(2013, 9, 30),
  "Report13-42-PA-708E-C20": datetime.datetime(2013, 9, 30),
  "Report13-43-PA-11055-C19-C20": datetime.datetime(2013, 9, 30),
  "Report14-01-KY-16444": datetime.datetime(2013, 11, 7),
  "Report14-02-KY-17066": datetime.datetime(2013, 12, 11),
  "Report14-03-AL-16763": datetime.datetime(2013, 12, 13),
  "Report14-04-PA-16279": datetime.datetime(2013, 12, 13),
  "Report14-05-KY-7779-C31C32": datetime.datetime(2014, 1, 31),
  "Report14-06-AL-16549-C-2": datetime.datetime(2014, 1, 16),
  "Report14-07-PA-16273-09": datetime.datetime(2014, 1, 31),
  "Report14-08-VA-16954": datetime.datetime(2014, 1, 13),
  "Report14-09FiscalYear2013FinancialStatementAudit": datetime.datetime(2014, 1, 29),
  "Report14-10-TN-16336": datetime.datetime(2014, 2, 22),
  "Report14-12-WV-12951-C9C10": datetime.datetime(2014, 3, 7),
  "Report14-13-VA-711B": datetime.datetime(2014, 3, 7),
  "Report14-14-GA-16235": datetime.datetime(2014, 3, 14),
  "Report14-15-OpenHUDGrants": datetime.datetime(2014, 3, 31),
  "Report14-16-OlderOpenBasicChildAgencyGrants": datetime.datetime(2014, 3, 31),
  "Report14-17-OlderOpenARCAdministeredGrants": datetime.datetime(2014, 3, 31),
  "Report14-18-AdministrativeReview": datetime.datetime(2014, 3, 31),
  "Report14-19-MS-17126": datetime.datetime(2014, 3, 28),
  "Report14-20-VA-16944": datetime.datetime(2014, 5, 12),
  "Report14-21-SC-17044": datetime.datetime(2014, 5, 9),
  "Report14-22-WV16738": datetime.datetime(2014, 5, 9),
  "Report14-23-WV-14334-C9C10": datetime.datetime(2014, 5, 9),
  "Report14-24-WV-17158": datetime.datetime(2014, 6, 2),
  "Report14-26-VA-17382": datetime.datetime(2014, 8, 15),
  "Report14-27-NY-2329C39C40": datetime.datetime(2014, 5, 12),
  "Report14-28-TN-17163": datetime.datetime(2014, 6, 16),
  "Report14-29-PA-8285-C31": datetime.datetime(2014, 7, 29),
  "Report14-30-PA-708A-C42": datetime.datetime(2014, 7, 29),
  "Report14-31-KY-17385": datetime.datetime(2014, 6, 20),
  "Report14-32-ARCVisaWaiverProgramKentucky": datetime.datetime(2014, 7, 29),
  "Report14-33-KY-16285": datetime.datetime(2014, 7, 17),
  "Report14-34-AL-17208-302-12": datetime.datetime(2014, 7, 31),
  "Report14-35-KY-16080-C3-C4": datetime.datetime(2014, 7, 23),
  "Report14-36-TN-16327": datetime.datetime(2014, 7, 23),
  "Report14-37-AL-17224": datetime.datetime(2014, 7, 23),
  "Report14-38-SC-16988": datetime.datetime(2014, 8, 21),
  "Report14-39-NewYorkVisaWaiverProgram": datetime.datetime(2014, 8, 27),
  "Report14-40-OpenHUDGrants": datetime.datetime(2014, 9, 30),
  "Report 14-41OlderOpenARCAdministeredGrants": datetime.datetime(2014, 9, 30),
  "Report 14-42-OlderOpenBasicChildAgencyGrants": datetime.datetime(2014, 9, 30),
  "Report14-43-OH-707C-C44": datetime.datetime(2014, 9, 19),
  "Report14-44-MOUsWithBasicAgencies": datetime.datetime(2014, 9, 30),
  "Report15-01-KY-17099": datetime.datetime(2014, 12, 12),
  "Report15-02FiscalYear2014FinancialStatementAudit": datetime.datetime(2014, 11, 25),
  "Report15-03-PA-708D-C41-C42": datetime.datetime(2015, 1, 30),
  "Report15-04-PA-8291-C31C32": datetime.datetime(2015, 1, 30),
  "Report15-05OpenFHWAGrants": datetime.datetime(2015, 1, 28),
  "Report15-06-NC-16688": datetime.datetime(2015, 1, 30),
  "Report15-07-TN-16710": datetime.datetime(2015, 2, 20),
  "Report15-08-PA-708B-C41C42": datetime.datetime(2015, 2, 20),
  "Report15-09-PA-8312-C31C32": datetime.datetime(2015, 3, 24),
  "Report15-10-ImplementationOfMOUBtwnARCAndUSDA-RDS": datetime.datetime(2015, 3, 13),
  "Report15-11-CO-13764-H-C2-C3": datetime.datetime(2015, 3, 20),
  "Report15-12-AreaDevelopmentGrantApplicationsAndApprovals": datetime.datetime(2015, 3, 27),
  "Report15-13-ReviewOfAnnualStateStrategyStatements": datetime.datetime(2015, 3, 27),
  "Report15-14-ADHS-UnobligatedBalances-UnpaidObligations": datetime.datetime(2015, 3, 27),
  "Report15-18-WV-2284-C40C41": datetime.datetime(2015, 4, 27),
  "Report15-19-MS-17623-1andC1": datetime.datetime(2015, 4, 20),
  "Report15-20-OlderOpenARCAdministeredGrants": datetime.datetime(2015, 5, 4),
  "Report15-21-OlderOpenBasicChildAgencyGrants": datetime.datetime(2015, 5, 5),
  "Report15-22-MS-704-C-C41andMS704-C-C42": datetime.datetime(2015, 5, 8),
  "Report15-23-TN-17541-I- C1": datetime.datetime(2015, 7, 6),
  "Report15-24-TN-17551and17551-C": datetime.datetime(2015, 7, 6),
  "Report15-25-AL-15573-C5andC6": datetime.datetime(2015, 6, 15),
  "Report15-26-AL-7805-C31-C32andC33": datetime.datetime(2015, 6, 15),
  "Report15-37-HUD-Deobligations": datetime.datetime(2016, 11, 1),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for report_type, url in REPORT_TYPES.items():
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("table p > a[href]")
    if not results:
      raise inspector.NoReportsFoundError("ARC (%s)" % report_type)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  report_url = urljoin(landing_url, result.get('href'))
  report_url = report_url.replace("../", "")
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  try:
    title = result.parent.find("em").text
  except AttributeError:
    try:
      title = result.parent.contents[0].text
    except AttributeError:
      title = result.parent.contents[0]

  # There's a typo in the link for this report, it points to the wrong file
  if report_id == "Report14-28-TN-17163" and title.find("Report on the Better Basics, Inc., Literacy Program for Clay, Jefferson") != -1:
    report_url = "http://www.arc.gov/images/aboutarc/members/IG/Report14-34-AL-17208-302-12.pdf"
    report_id = "Report14-34-AL-17208-302-12"

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    try:
      published_on_text = title.split("\u2013")[-1].strip()
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except ValueError:
      pass

  if not published_on:
    try:
      response = utils.scraper.request(method="HEAD", url=report_url)
      last_modified = response.headers["Last-Modified"]
      published_on = datetime.datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
      pass

  if not published_on:
    admin.log_no_date("arc", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'arc',
    'inspector_url': 'http://www.arc.gov/oig',
    'agency': 'arc',
    'agency_name': 'Appalachian Regional Commission',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': report_type,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
