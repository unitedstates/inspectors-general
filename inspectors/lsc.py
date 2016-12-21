#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin, unquote

from bs4 import Tag, NavigableString, Comment
from utils import utils, inspector, admin

# https://www.oig.lsc.gov
archive = 1994

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

SEMIANNUAL_REPORTS_URL = "https://www.oig.lsc.gov/products/sar"
AUDIT_REPORTS_URL = "https://www.oig.lsc.gov/products/audit-reports"
INVESTIGATIONS_URL = "https://www.oig.lsc.gov/products/investigative-results-and-products"
PEER_REVIEWS_URL = "https://www.oig.lsc.gov/products/peer-reviews"
SEMIANNUAL_REPORTS_ARCHIVE_URL = "https://www.oig.lsc.gov/products/report-archives/sar-archives"
AUDIT_REPORTS_ARCHIVE_URL = "https://www.oig.lsc.gov/products/report-archives/audit-reports"
OTHER_REPORTS_ARCHIVE_URL = "https://www.oig.lsc.gov/products/report-archives/other-reports"
MAPPING_PROJECT_ARCHIVE_URL = "https://www.oig.lsc.gov/products/report-archives/mapping-project"
MAPPING_PROJECT_ARCHIVE_GRANTEE_URL = "https://www.oig.lsc.gov/grantee-evaluation"

REPORT_PUBLISHED_MAP = {
  "fraud-alert-15-02": datetime.datetime(2015, 4, 22),
  "fraud_alert_12-01-JS": datetime.datetime(2012, 1, 18),
  "check_fraud_attachment": datetime.datetime(2012, 1, 18),
  "lscoighotline": datetime.datetime(2008, 12, 17),
  "Dec_2006_Fraud_Alert": datetime.datetime(2006, 12, 11),
  "2014-report-to-nations": datetime.datetime(2014, 1, 1),
  "TIS_SASS_1014_LSC_OIG": datetime.datetime(2014, 10, 1),
  "MeekerOIGMappingReport": datetime.datetime(2005, 9, 14),
  "core-legal-services": datetime.datetime(2005, 3, 14),
  "Mapping_Evaluation_Phase_I_Volume_I_Final_Report": datetime.datetime(2003, 11, 1),
  "EvalICLS": datetime.datetime(2005, 11, 1),
  "EvalLAFLA": datetime.datetime(2004, 11, 1),
  "EvalLASOC": datetime.datetime(2004, 11, 1),
  "EvalLASSD": datetime.datetime(2004, 11, 1),
  "EvalNLS": datetime.datetime(2004, 11, 1),
  "EvalALAS": datetime.datetime(2005, 11, 1),
  "EvalGLSP": datetime.datetime(2005, 11, 1),
  "EvalMLSA": datetime.datetime(2005, 11, 1),
  "fraud-alert-16-01": datetime.datetime(2015, 10, 19),
  "15-029": datetime.datetime(2015, 9, 30),
  "17-01": datetime.datetime(2016, 12, 20),
  "16-10": datetime.datetime(2016, 9, 30),
  "16-09": datetime.datetime(2016, 9, 27),
  "16-08": datetime.datetime(2016, 9, 28),
  "16-07": datetime.datetime(2016, 7, 20),
  "16-06": datetime.datetime(2016, 6, 16),
  "16-05": datetime.datetime(2016, 3, 30),
  "16-04": datetime.datetime(2016, 3, 14),
  "16-03": datetime.datetime(2015, 12, 7),
  "16-02": datetime.datetime(2015, 12, 3),
  "16-01": datetime.datetime(2015, 11, 23),
  "15-12": datetime.datetime(2015, 9, 30),
  "15-11": datetime.datetime(2015, 9, 29),
  "15-10": datetime.datetime(2015, 8, 20),
  "15-09": datetime.datetime(2015, 7, 9),
  "15-08": datetime.datetime(2015, 7, 7),
  "15-07": datetime.datetime(2015, 5, 27),
  "15-06": datetime.datetime(2015, 5, 4),
  "15-05": datetime.datetime(2015, 3, 26),
  "15-04": datetime.datetime(2015, 3, 30),
  "15-03": datetime.datetime(2015, 2, 2),
  "15-02": datetime.datetime(2015, 1, 27),
  "15-01": datetime.datetime(2014, 10, 9),
  "14-08": datetime.datetime(2014, 8, 7),
  "14-07": datetime.datetime(2014, 7, 10),
  "14-06": datetime.datetime(2014, 6, 30),
  "14-05": datetime.datetime(2014, 6, 9),
  "14-04": datetime.datetime(2014, 5, 15),
  "14-03": datetime.datetime(2014, 5, 6),
  "14-02": datetime.datetime(2014, 3, 26),
  "14-01": datetime.datetime(2014, 3, 24),
  "04-07": datetime.datetime(2004, 8, 27),
  "04-06": datetime.datetime(2004, 8, 25),
  "04-05": datetime.datetime(2004, 8, 10),
  "04-03": datetime.datetime(2004, 3, 9),
  "04-02": datetime.datetime(2003, 12, 11),
  "04-01": datetime.datetime(2004, 1, 29),
  "03-06": datetime.datetime(2003, 9, 30),
  "03-05": datetime.datetime(2003, 9, 26),
  "03-03": datetime.datetime(2003, 6, 24),
  "03-02": datetime.datetime(2003, 3, 26),
  "03-01": datetime.datetime(2002, 12, 16),
  "02-03": datetime.datetime(2002, 3, 18),
  "02-01": datetime.datetime(2001, 10, 30),
  "FY2001_Audit_of_the_Corporation": datetime.datetime(2001, 11, 30),
  "01-005": datetime.datetime(2001, 9, 25),
  "01-004": datetime.datetime(2001, 8, 1),
  "01-003": datetime.datetime(2001, 6, 8),
  "01-002": datetime.datetime(2001, 3, 15),
  "FY2000_Audit_of_the_Corporation": datetime.datetime(2000, 11, 23),
  "00-006": datetime.datetime(2000, 9, 29),
  "00-004": datetime.datetime(2000, 2, 1),
  "00-002": datetime.datetime(1999, 12, 1),
  "00-001": datetime.datetime(1999, 11, 1),
  "FY1999_Audit_of_the_Corporation": datetime.datetime(2000, 1, 14),
  "99-021": datetime.datetime(1999, 9, 1),
  "99-020": datetime.datetime(1999, 9, 1),
  "99-019": datetime.datetime(1999, 9, 1),
  "99-018": datetime.datetime(1999, 9, 1),
  "99-017": datetime.datetime(1999, 8, 1),
  "99-016": datetime.datetime(1999, 7, 21),
  "99-015": datetime.datetime(1999, 7, 1),
  "99-014": datetime.datetime(1999, 5, 1),
  "99-013": datetime.datetime(1999, 3, 1),
  "99-012": datetime.datetime(1999, 3, 1),
  "99-001": datetime.datetime(1998, 10, 1),
  "FY1998_Audit_of_the_Corporation": datetime.datetime(1998, 11, 25),
  "FY1997_Audit_of_the_Corporation": datetime.datetime(1997, 11, 21),
  "97-002": datetime.datetime(1997, 7, 30),
  "FY1996_Audit_of_the_Corporation": datetime.datetime(1996, 12, 2),
  "96-062": datetime.datetime(1998, 2, 1),
  "96-063A": datetime.datetime(1997, 9, 1),
  "96-063B": datetime.datetime(1997, 12, 1),
  "96-063C": datetime.datetime(1997, 9, 1),
  "96-063D": datetime.datetime(1997, 12, 1),
  "96-063E": datetime.datetime(1997, 9, 1),
  "96-063F": datetime.datetime(1997, 9, 1),
  "96-063G": datetime.datetime(1997, 9, 1),
  "96-063H": datetime.datetime(1997, 9, 1),
  "96-064A": datetime.datetime(1997, 9, 1),
  "96-064B": datetime.datetime(1997, 9, 1),
  "96-064C": datetime.datetime(1997, 9, 1),
  "96-064D": datetime.datetime(1997, 12, 1),
  "96-064E": datetime.datetime(1997, 9, 1),
  "96-064F": datetime.datetime(1997, 9, 1),
  "96-064G": datetime.datetime(1997, 9, 1),
  "96-064H": datetime.datetime(1997, 9, 1),
  "93-067": datetime.datetime(1994, 5, 4),
  "Fiscal_Matters_Final_Report": datetime.datetime(2006, 9, 25),
  "LSCManagementStatementRegardingOIGReportOnCertainFiscalPracticesAtLSC": datetime.datetime(2006, 9, 26),
  "CRLA0603": datetime.datetime(2006, 9, 14),
  "KW092606": datetime.datetime(2006, 9, 26),
  "mg060719": datetime.datetime(2006, 7, 19),
  "kw060727": datetime.datetime(2006, 7, 27),
  "Financial_Implications_of_the_Lease_Report": datetime.datetime(2005, 4, 22),
  "CTF-03-002": datetime.datetime(2003, 3, 6),
  "CTF-03-001": datetime.datetime(2002, 11, 1),
  "CTF-02-005": datetime.datetime(2002, 9, 10),
  "CTF-02-004": datetime.datetime(2002, 9, 10),
  "CTF-02-003": datetime.datetime(2002, 9, 9),
  "CTF-02-002": datetime.datetime(2001, 12, 18),
  "CTF-02-001": datetime.datetime(2001, 11, 6),
  "CTF-01-008": datetime.datetime(2001, 11, 9),
  "CTF-01-007": datetime.datetime(2001, 10, 11),
  "CTF-01-006": datetime.datetime(2001, 9, 27),
  "CTF-01-005": datetime.datetime(2001, 8, 22),
  "CTF-01-004": datetime.datetime(2001, 7, 23),
  "CTF-01-003": datetime.datetime(2001, 5, 8),
  "CTF-01-002": datetime.datetime(2001, 4, 9),
  "CTF-01-001": datetime.datetime(2001, 3, 20),
  "CTF-00-013": datetime.datetime(2000, 12, 13),
  "CTF-00-012": datetime.datetime(2000, 10, 13),
  "CTF-00-011": datetime.datetime(2000, 9, 8),
  "INP00-011b": datetime.datetime(2000, 9, 8),
  "CTF-00-010": datetime.datetime(2000, 8, 9),
  "INP00-010a": datetime.datetime(2000, 8, 9),
  "CTF-00-008": datetime.datetime(2000, 6, 8),
  "INP00-008a": datetime.datetime(2000, 6, 8),
  "INP00-008b": datetime.datetime(2000, 6, 8),
  "CTF-00-006": datetime.datetime(2000, 5, 12),
  "CTF-00-005": datetime.datetime(2000, 3, 24),
  "CTF-00-003": datetime.datetime(2000, 2, 4),
  "special-report-00-001": datetime.datetime(2000, 7, 30),
  "assessment_of_compliance_Sept1999": datetime.datetime(1999, 10, 29),
  "CTF-99-020": datetime.datetime(2000, 1, 3),
  "CTF-99-015": datetime.datetime(1999, 9, 17),
  "CTF-99-011": datetime.datetime(1999, 9, 30),
  "CTF-99-010": datetime.datetime(1999, 9, 16),
  "CTF-99-008": datetime.datetime(1999, 5, 5),
  "CTF-99-007": datetime.datetime(1999, 5, 1),
  "CTF-99-006": datetime.datetime(1999, 3, 26),
  "CTF-99-004": datetime.datetime(1999, 2, 26),
  "Survey_of_LSCGrantees": datetime.datetime(1998, 2, 1),
  "96-040": datetime.datetime(1997, 1, 1),
  "95-035": datetime.datetime(1996, 8, 1),
  "95-096": datetime.datetime(1995, 7, 18),
}

BLACKLIST_REPORT_TITLES = [
  'PDF',
  'Word97',
  'WP5.1',
  'LSC Management Response',
  'Summary of Audit Findings and Recommendations',
  'Client Trust Fund Inspection Reports',
]

def parse_year_accordion(content, landing_url, report_type, year_range):
  accordions = content.select("div.accordion-group")
  if not accordions:
    raise inspector.NoReportsFoundError("Legal Services Corporation (%s)" %
                                        landing_url)
  for accordion in accordions:
    heading = accordion.select("div.accordion-heading")[0]
    year_text = inspector.sanitize(heading.text)
    body = accordion.select("div.accordion-body div.accordion-inner")[0]
    if year_text == "FY1995" and body.text.strip() == "FY1995":
      continue
    results = [a for a in body.find_all("a") if a.text.strip()]
    if not results:
      raise inspector.NoReportsFoundError("Legal Services Corporation (%s)" %
                                          landing_url)
    for result in results:
      report = report_from(result, landing_url, report_type, year_range)
      if report:
        inspector.save_report(report)

def parse_investigation(content, landing_url, report_type, year_range):
  doj_flag = True
  doj_report_counter = 0
  other_report_counter = 0
  for child in content.children:
    if (isinstance(child, Tag) and
        child.name == 'h3' and
        child.text == 'Reports'):
      doj_flag = False
      continue
    if doj_flag:
      if isinstance(child, Tag) and child.name == 'ul':
        doj_report_counter = doj_report_counter + 1
        report = report_from(child.li, landing_url, report_type, year_range)
        if report:
          inspector.save_report(report)
    else:
      if isinstance(child, Tag):
        if child.name != 'h3' and child.text.strip():
          other_report_counter = other_report_counter + 1
          report = report_from(child, landing_url, report_type, year_range)
          if report:
            inspector.save_report(report)
      elif isinstance(child, Comment):
        continue
      elif isinstance(child, NavigableString):
        if child.strip():
          raise Exception("Unexpected text!: " + child)
  if doj_report_counter == 0 or other_report_counter == 0:
    raise inspector.NoReportsFoundError("Legal Services Corporation (%s)" % landing_url)

def parse_peer_reviews(content, landing_url, report_type, year_range):
  links = content.find_all("a")
  if len(links) <= 1:
    raise inspector.NoReportsFoundError("Legal Services Corporation (%s)" % landing_url)
  for link in links:
    if link.text.find("Government Auditing Standards") != -1:
      continue
    result = link.parent
    report = report_from(result, landing_url, report_type, year_range)
    if report:
      inspector.save_report(report)

def parse_mapping(content, landing_url, report_type, year_range):
  links = content.find_all("a")
  if not links:
    raise inspector.NoReportsFoundError("Legal Services Corporation (%s)" % landing_url)
  for link in links:
    href = link.get("href")
    href = urljoin(landing_url, href)
    result = None
    if href == "https://www.oig.lsc.gov/images/mapping/mapping.zip":
      continue
    elif href == MAPPING_PROJECT_ARCHIVE_GRANTEE_URL:
      continue
    elif href.startswith("mailto:"):
      continue
    elif href == "https://www.oig.lsc.gov/evaluation-of-legal-services-mapping-prsentation":
      link["href"] = "https://oig.lsc.gov/mapping/phaseIIbriefing.pdf"
      result = link.parent
    elif href in ("https://www.oig.lsc.gov/images/pdfs/mapping/MeekerOIGMappingReport.pdf",
                  "https://www.oig.lsc.gov/core-legal-services",):
      result = link.parent
    elif href == "https://www.oig.lsc.gov/images/mapping/Mapping_Evaluation_Phase_I_Volume_I_Final_Report.pdf":
      result = link.parent.parent
    elif (href.startswith("https://www.oig.lsc.gov/images/pdfs/mapping/Eval") and
          href.endswith(".pdf")):
      result = link.parent
    elif (href.startswith("https://www.oig.lsc.gov/images/mapping/references/"
                          "Eval") and
          href.endswith(".pdf")):
      result = link.parent
    elif (href.startswith("https://www.oig.lsc.gov/images/Eval") and
          href.endswith(".pdf")):
      result = link.parent
    else:
      raise Exception("Unexpected link found on a mapping project page: %s"
                      % href)

    report = report_from(result, landing_url, report_type, year_range)
    if report:
      inspector.save_report(report)

REPORT_PAGES_INFO = [
  (SEMIANNUAL_REPORTS_URL, "semiannual_report", parse_year_accordion),
  (AUDIT_REPORTS_URL, "audit", parse_year_accordion),
  (INVESTIGATIONS_URL, "investigation", parse_investigation),
  (PEER_REVIEWS_URL, "other", parse_peer_reviews),
  (SEMIANNUAL_REPORTS_ARCHIVE_URL, "semiannual_report", parse_year_accordion),
  (AUDIT_REPORTS_ARCHIVE_URL, "audit", parse_year_accordion),
  (OTHER_REPORTS_ARCHIVE_URL, "other", parse_year_accordion),
  (MAPPING_PROJECT_ARCHIVE_URL, "other", parse_mapping),
  (MAPPING_PROJECT_ARCHIVE_GRANTEE_URL, "other", parse_mapping),
]

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for url, report_type, parse_func in REPORT_PAGES_INFO:
    doc = utils.beautifulsoup_from_url(url)

    content = doc.select("section.article-content")[0]
    parse_func(content, url, report_type, year_range)

REPORT_NO_RE = re.compile("[0-9]{2}-[0-9]{2,3}[A-Z]?")

def report_from(result, landing_url, report_type, year_range):
  if not result.text or result.text in BLACKLIST_REPORT_TITLES:
    # There are a few empty links due to bad html and some links for alternative
    # formats (PDF) that we will just ignore.
    return

  link_text = None
  if result.name == 'a':
    report_url = result.get('href')
    link_text = inspector.sanitize(result.text)
    title = inspector.sanitize("%s %s" % (result.text, result.next_sibling))
  else:
    links = [link for link in result.find_all('a') if link.text.strip()]
    report_url = links[0].get('href')
    link_text = inspector.sanitize(result.a.text)
    title = inspector.sanitize(result.text)
  report_url = urljoin(landing_url, report_url)
  report_filename = os.path.basename(report_url)

  if title.endswith("PDF"):
    title = title[:-3]
  title = title.rstrip(" .")

  prev = result.previous_sibling
  if isinstance(prev, NavigableString) and "See, also:" in prev:
    return None

  report_no_match = REPORT_NO_RE.match(link_text)
  if report_no_match:
    report_id = report_no_match.group(0)
    if "fraud" in report_url.lower():
      report_id = "fraud-alert-" + report_id
    elif "Client_Trust_Fund" in report_url:
      report_id = "CTF-" + report_id
    elif report_filename.startswith("sr"):
      report_id = "special-report-" + report_id
  else:
    report_id, _ = os.path.splitext(report_filename)
    report_id = unquote(report_id)
  report_id = "-".join(report_id.split())
  report_id = report_id.replace("\\", "") # strip backslashes

  estimated_date = False
  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  elif link_text == "June 2015":
    published_on = datetime.datetime(2015, 6, 1)
  else:
    published_on_text = None
    try:
      published_on_text = re.search('(\d+/\d+/\d+)', title).groups()[0]
    except AttributeError:
      pass
    if not published_on_text:
      try:
        published_on_text = re.search('(\w+ \d+, \d+)', title).groups()[0]
      except AttributeError:
        pass
    if not published_on_text:
      try:
        published_on_text = re.search('(\d+/\d+)', title).groups()[0]
      except AttributeError:
        pass

    if not published_on_text:
      admin.log_no_date("lsc", report_id, title, report_url)
      return

    if not published_on:
      datetime_formats = [
        '%B %d, %Y',
        '%m/%d/%Y',
        '%m/%d/%y',
        '%m/%Y',
        '%m/%y'
      ]
      for datetime_format in datetime_formats:
        try:
          published_on = datetime.datetime.strptime(published_on_text, datetime_format)
        except ValueError:
          pass
        else:
          break

  if not published_on:
    admin.log_no_date("lsc", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'lsc',
    'inspector_url': 'https://www.oig.lsc.gov',
    'agency': 'lsc',
    'agency_name': 'Legal Services Corporation',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  if estimated_date:
    report['estimated_date'] = estimated_date

  if report_url in ("https://www.oig.lsc.gov/core-legal-services"):
    report['file_type'] = "html"

  if report_url.startswith("https://oig.lsc.gov/mapping/references/eval"):
    report['unreleased'] = True
    report['missing'] = True

  return report

utils.run(run) if (__name__ == "__main__") else None
