#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# http://www.fec.gov/fecig/fecig.shtml
archive = 1994

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - In the Audit Reports section, there are two seprate ul elements.
# - It would be useful if all of the reports displayed published dates.
# - It would be nice to add reports for pages like this:
# http://www.fec.gov/fecig/transit.htm
# - There are two broken links due to an extra "_000" or "_001" in link targets

REPORTS_URL = "http://www.fec.gov/fecig/fecig.shtml"

REPORT_PUBLISHED_MAPPING = {
  "Final-QualityAssessmentAuditoftheFECAuditDivision-OIG-12-01": datetime.datetime(2012, 9, 1),
  "FinalPeerReviewReport-FarmCreditAdmin": datetime.datetime(2017, 2, 15),
  "property": datetime.datetime(2010, 3, 1),
  "procurement": datetime.datetime(2009, 9, 1),
  "disclosure": datetime.datetime(2005, 12, 1),
  "training": datetime.datetime(2000, 7, 1),
  "Y2K": datetime.datetime(1999, 5, 1),
  "InvestigativePeerReviewbySEC": datetime.datetime(2013, 9, 23),
  "FECDRPandCOOPInspectionReport": datetime.datetime(2013, 1, 1),
  "ContractSecuritya": datetime.datetime(2012, 8, 1),
  "KastleKeyInspectionReport": datetime.datetime(2011, 12, 1),
  "oep": datetime.datetime(2002, 2, 1),
  "retire": datetime.datetime(2001, 12, 1),
  "westlaw": datetime.datetime(2001, 7, 1),
  "fmfia": datetime.datetime(2001, 6, 1),
  "internet": datetime.datetime(2001, 5, 1),
  "AuditoftheFECsTeleworkPrograms-June2016-OIG-15-03-Final": datetime.datetime(2016, 6, 1),
  "FY2016FinancialStatementAuditReport-Final": datetime.datetime(2016, 11, 15),
  "FY2015FinancialStatementAuditReport-Final": datetime.datetime(2015, 11, 16),
  "FEC2014FinancialStatementAuditReport": datetime.datetime(2014, 11, 17),
  "FY2013FinancialStatementAuditReport": datetime.datetime(2013, 12, 13),
  "HRaudit2013": datetime.datetime(2013, 7, 9),
  "FY12FinancialStatementAuditReport": datetime.datetime(2012, 12, 14),
  "Final_FY2011_Financial_Statement_Audit_Report": datetime.datetime(2011, 11, 14),
  "ProcurementandContractManagement2010": datetime.datetime(2011, 6, 6),
  "2010PrivacyReport": datetime.datetime(2011, 3, 31),
  "financial10": datetime.datetime(2010, 11, 12),
  "financial09": datetime.datetime(2009, 11, 13),
  "financial08": datetime.datetime(2008, 11, 12),
  "2007Privacy": datetime.datetime(2007, 12, 7),
  "financial07": datetime.datetime(2007, 11, 15),
  "transit07": datetime.datetime(2007, 2, 1),
  "financial06": datetime.datetime(2006, 11, 15),
  "financial05": datetime.datetime(2005, 11, 10),
  "financial04": datetime.datetime(2004, 12, 16),
  "IGStatementonFECManagementandPerformanceChallenges-2016-Final": datetime.datetime(2016, 10, 19),
  "RootCausesofLowEmployeeMoraleStudy-FinalReport-OIG-15-06": datetime.datetime(2016, 7, 1),
  "ManagementandPerformanceChallenges-2015-FinalReport": datetime.datetime(2015, 10, 16),
  "ReviewofCompletedCorrectiveActionsofFY2014FinancialStatementAudit-December2014_000": datetime.datetime(2014, 12, 9),
  "FinalReport-InspectionoftheFECsTravelandPurchaseCardPrograms-OIG-14-05-June2015": datetime.datetime(2015, 2, 1),
  "2014ManagementChallenges-IncludesIGStatementandManagementsResponse": datetime.datetime(2014, 10, 15),
  "FEC-A-123InspectionReport-Final06-17-14-assessed": datetime.datetime(2014, 6, 10),
  "FECOIG_Peer_Review_2013": datetime.datetime(2014, 2, 11),
  "Final-SurveyoftheFECsNewEmployeeOrientationProgram-OIG12-08": datetime.datetime(2012, 9, 1),
  "PeerReview2010": datetime.datetime(2011, 5, 5),
  "transit09": datetime.datetime(2009, 7, 1),
}


def run(options):
  year_range = inspector.year_range(options, archive)

  doc = utils.beautifulsoup_from_url(REPORTS_URL)

  # Pull the audit reports
  audit_header = doc.find("a", attrs={"name": 'Audit Reports'})
  audit_list1 = audit_header.find_next("ul").select("li")
  # They have two separate uls for these reports. See note to the IG web team.
  audit_list2 = audit_header.find_next("ul").find_next("ul").select("li")
  results = audit_list1 + audit_list2
  if not results:
    raise inspector.NoReportsFoundError("FEC (audit reports)")
  for result in results:
    report = report_from(result, year_range, report_type='audit')
    if report:
      inspector.save_report(report)

  # Pull the inspection reports
  inspections_header = doc.find("a", attrs={"name": 'Inspection Reports'})
  results = inspections_header.find_next("ul").select("li")
  if not results:
    raise inspector.NoReportsFoundError("FEC (inspection reports)")
  for result in results:
    report = report_from(result, year_range, report_type='inspection')
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  semiannual_header = doc.find("a", attrs={"name": 'Semiannual Reports'})
  results = semiannual_header.find_next("ul").select("li")
  ul1 = semiannual_header.find_next("ul")
  ul2 = ul1.find_next("ul")
  results = ul1.select("li") + ul2.select("li")
  if not results:
    raise inspector.NoReportsFoundError("FEC (semiannual reports)")
  for result in results:
    if not result.text:
      continue
    report = report_from(result, year_range, report_type='semiannual_report', title_prefix="Semiannual Report - ")
    if report:
      inspector.save_report(report)


def report_from(result, year_range, report_type, title_prefix=None):
  report_url = urljoin(REPORTS_URL, result.select("a")[-1].get("href"))

  # Temporary hacks to account for link mistakes
  if report_url == "http://www.fec.gov/fecig/documents/Semi14a_000.pdf":
    report_url = "http://www.fec.gov/fecig/documents/Semi14a.pdf"
  if report_url == "http://www.fec.gov/fecig/documents/ReviewofOutstanding" \
                   "RecommendationsasofJune2014_001.pdf":
    report_url = "http://www.fec.gov/general/documents/ReviewofOutstanding" \
                 "RecommendationsasofJune2014.pdf"

  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on = None
  if report_url.endswith(".pdf"):
    # Inline report
    title = inspector.sanitize(result.contents[0].strip().rstrip("-"))
    title = re.sub("\\s+", " ", title)
    if title.endswith((" 200", " 201")):
      # some years are split up by a <span> tag
      title = title + result.contents[1].text
  else:
    # Some pages have separate landing pages.
    doc = utils.beautifulsoup_from_url(report_url)
    title = doc.select("h3")[1].text.strip()
    try:
      published_on_text = doc.select("h3")[2].text.strip()
    except IndexError:
      published_on_text = doc.select("h3")[1].text.strip()
    published_on_text = published_on_text.replace("Period ending ", "")
    published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if title == "November 2016" and report_url == "http://www.fec.gov/fecig/documents/OIGSemiannualReporttoCongress-May2016-FinalPublicDistribution.pdf":
    # Fix copy-paste error
    report_url = "http://www.fec.gov/fecig/documents/OIGFall2016SARFINAL.pdf"
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)

  if not published_on:
    if report_id in REPORT_PUBLISHED_MAPPING:
      published_on = REPORT_PUBLISHED_MAPPING[report_id]
  if not published_on:
    try:
      published_on_text = "-".join(re.search('(\w+)\s+(\d{4})', title).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B-%Y')
    except (ValueError, AttributeError):
      pass

  if title_prefix:
    title = "{}{}".format(title_prefix, title)

  if not published_on:
    admin.log_no_date("fec", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "fec",
    'inspector_url': "http://www.fec.gov/fecig/fecig.shtml",
    'agency': "fec",
    'agency_name': "Federal Election Commission",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),  # Date of publication
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
