#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin, unquote

from bs4 import Tag, NavigableString, Comment
from utils import utils, inspector

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
  "14-06": datetime.datetime(2014, 6, 30),
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
    if year_text.startswith("FY"):
      year = int(year_text[2:])
    else:
      year = int(year_text)
    body = accordion.select("div.accordion-body div.accordion-inner")[0]
    if year_text == "FY1995" and body.text.strip() == "FY1995":
      continue
    results = [a for a in body.find_all("a") if a.text.strip()]
    if not results:
      raise inspector.NoReportsFoundError("Legal Services Corporation (%s)" %
                                          landing_url)
    for result in results:
      report = report_from(result, landing_url, report_type, year_range, year)
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
        report = report_from(child.li, landing_url, report_type, year_range)
        if report:
          inspector.save_report(report)
          doj_report_counter = doj_report_counter + 1
    else:
      if isinstance(child, Tag):
        if child.name != 'h3' and child.text.strip():
          report = report_from(child, landing_url, report_type, year_range)
          if report:
            inspector.save_report(report)
            other_report_counter = other_report_counter + 1
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

def report_from(result, landing_url, report_type, year_range, year=None):
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
      if year is None:
        raise Exception("No date or year was detected for %s (%s)" %
                        (report_id, title))
      # Since we only have the year, set this to Nov 1st of that year
      published_on = datetime.datetime(year, 11, 1)
      estimated_date = True

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
