#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin, unquote

from utils import utils, inspector, admin

# https://www.treasury.gov/about/organizational-structure/ig/Pages/audit_reports_index.aspx
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add an agency for report 'OIG-09-015' listed on
# https://www.treasury.gov/about/organizational-structure/ig/Pages/by-date-2009.aspx
# - There is an extra tr.ms-rteTableEvenRow-default at the end of
# https://www.treasury.gov/about/organizational-structure/ig/Pages/by-date-2014.aspx
# - Add published dates for all reports at
# https://www.treasury.gov/about/organizational-structure/ig/Pages/other-reports.aspx
# - OIG-07-003 is posted twice, once with the wrong date

AUDIT_REPORTS_BASE_URL = "https://www.treasury.gov/about/organizational-structure/ig/Pages/by-date-{}.aspx"
TESTIMONIES_URL = "https://www.treasury.gov/about/organizational-structure/ig/Pages/testimony_index.aspx"
PEER_AUDITS_URL = "https://www.treasury.gov/about/organizational-structure/ig/Pages/peer_audit_reports_index.aspx"
OTHER_REPORTS_URL = "https://www.treasury.gov/about/organizational-structure/ig/Pages/other-reports.aspx"
SEMIANNUAL_REPORTS_URL = "https://www.treasury.gov/about/organizational-structure/ig/Pages/semiannual_reports_index.aspx"

AGENCY_NAMES = {
  "bep": "The Bureau of Engraving & Printing",
  "bfs": "The Bureau of the Fiscal Service",
  "bpd": "The Bureau of the Public",
  "cdfi": "The Community Development Financial Institution Fund",
  "cfpb": "Consumer Financial Protection Bureau",
  "do": "Department of the Treasury",
  "esf": "Exchange Stabilization Fund",
  "ffb": "Federal Financing Bank",
  "fcen": "The Financial Crimes Enforcement Network",
  "fincen": "The Financial Crimes Enforcement Network", # Another slug for the above
  "fms": "Financial Management Service",
  "gcerc": "Gulf Coast Ecosystem Restoration Council",
  "ia": "The Office of International Affairs",
  "mint": "The U.S. Mint",
  "occ": "The Office of the Comptroller of the Currency",
  "odcp": "Office of DC Pensions",
  "ofac": "The Office of Foreign Assets Control",
  "ofr": "Office of Financial Research",
  "oig": "Office of the Inspector General",
  "ots": "The Office of Thrift",
  "restore": "The RESTORE Act",
  "sblf": "Small Business Lending Fund",
  "ssbci": "State Small Business Credit Initiative",
  "tfi": "Office of Terrorism and Financial Intelligence",
  "ttb": "The Alcohol and Tobacco Tax and Trade Bureau",
  "tff": "Treasury Forfeiture Fund",
}

OTHER_URLS = {
  "testimony": TESTIMONIES_URL,
  "peer_review": PEER_AUDITS_URL,
  "other": OTHER_REPORTS_URL,
}

UNRELEASED_REPORTS = [
  # These reports do not say they are unreleased, but there are no links
  "IGATI 2006",
  "IGATI 2007",
  "OIG-CA-07-001",
  "OIG-08-039",
  "OIG-08-013",
]

REPORT_AGENCY_MAP = {
  "OIG-09-015": "mint",  # See note to IG web team
}

REPORT_PUBLISHED_MAP = {
  "OIG-CA-13-006": datetime.datetime(2013, 3, 29),
  "OIG-13-CA-008": datetime.datetime(2013, 6, 10),
  "Treasury Freedom of Information Act (FOIA) Request Review": datetime.datetime(2010, 11, 19),
  "OIG-CA-14-017": datetime.datetime(2014, 9, 30),
  "OIG-CA-14-015": datetime.datetime(2014, 9, 4),
  "OIG-CA-15-023": datetime.datetime(2015, 7, 29),
  "OIG-CA-15-020": datetime.datetime(2015, 6, 22),
  "OIG-15-CA-012": datetime.datetime(2015, 4, 7),
  "OIG-CA-15-024": datetime.datetime(2015, 9, 15),
  "M-12-12 Reporting": datetime.datetime(2016, 1, 28),
  "OIG-CA-16-012": datetime.datetime(2016, 3, 30),
  "OIG-CA-16-014": datetime.datetime(2016, 4, 19),
  "Role of Non-Career Officials in Treasury FOIA Processing": datetime.datetime(2016, 3, 9),
  "OIG-CA-16-028": datetime.datetime(2016, 6, 30),
  "OIG-CA-16-033A": datetime.datetime(2016, 7, 29),
  "OIG-CA-16-033B": datetime.datetime(2016, 7, 29),
}

def run(options):
  year_range = inspector.year_range(options, archive)
  if datetime.datetime.now().month >= 10:
    # October, November, and December fall into the next fiscal year
    # Add next year to year_range to compensate
    year_range.append(max(year_range) + 1)

  # Pull the audit reports
  for year in year_range:
    if year < 2006:  # This is the oldest year for these reports
      continue
    url = AUDIT_REPORTS_BASE_URL.format(year)
    doc = utils.beautifulsoup_from_url(url)
    results = doc.find_all("tr", class_=["ms-rteTableOddRow-default",
                                         "ms-rteTableEvenRow-default"])
    if not results:
      raise inspector.NoReportsFoundError("Treasury (%d)" % year)
    for result in results:
      report = audit_report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

  for report_type, url in OTHER_URLS.items():
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("#ctl00_PlaceHolderMain_ctl05_ctl01__ControlWrapper_RichHtmlField > p a")
    if not results:
      raise inspector.NoReportsFoundError("Treasury (%s)" % report_type)
    for result in results:
      if len(result.parent.find_all("a")) == 1:
        result = result.parent
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("#ctl00_PlaceHolderMain_ctl05_ctl01__ControlWrapper_RichHtmlField > p > a")
  if not results:
    raise inspector.NoReportsFoundError("Treasury (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, SEMIANNUAL_REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

def clean_text(text):
  # A lot of text on this page has extra characters
  return text.replace('\u200b', '').replace('\ufffd', ' ').replace('\xa0', ' ').strip()

SUMMARY_RE = re.compile("(OIG|OIG-CA|EVAL) *-? *([0-9]+) *- *([0-9R]+) *[:,]? +([^ ].*)")
SUMMARY_FALLBACK_RE = re.compile("([0-9]+)-(OIG)-([0-9]+) *:? *(.*)")

def audit_report_from(result, page_url, year_range):
  if not clean_text(result.text):
    # Empty row
    return

  # Get all direct child nodes
  children = list(result.find_all(True, recursive=False))
  published_on_text = clean_text(children[1].text)

  # this is the header row
  if published_on_text.strip() == "Date":
    return None

  date_formats = ['%m/%d/%Y', '%m/%d%Y']
  published_on = None
  for date_format in date_formats:
    try:
      published_on = datetime.datetime.strptime(published_on_text, date_format)
    except ValueError:
      pass

  report_summary = clean_text(children[2].text)
  if not report_summary:
    # There is an extra row that we want to skip
    return

  report_summary = report_summary.replace("OIG-15-38Administrative",
                                          "OIG-15-38 Administrative")
  summary_match = SUMMARY_RE.match(report_summary)
  summary_match_2 = SUMMARY_FALLBACK_RE.match(report_summary)
  if summary_match:
    report_id = summary_match.expand(r"\1-\2-\3")
    title = summary_match.group(4)
  elif summary_match_2:
    report_id = summary_match_2.expand(r"(\2-\1-\3")
    title = summary_match_2.group(4)
  elif report_summary.startswith("IGATI") and published_on is not None:
    # There are two such annual reports from different years, append the year
    report_id = "IGATI %d" % published_on.year
    title = report_summary
  elif report_summary == "Report on the Bureau of the Fiscal Service Federal " \
      "Investments Branch\u2019s Description of its Investment/" \
      "Redemption Services and the Suitability of the Design and Operating " \
      "Effectiveness of its Controls for the Period August 1, 2013 to " \
      "July 31, 2014":
    # This one is missing its ID on the index
    report_id = "OIG-14-049"
    title = report_summary
  elif report_summary == "Correspondence related to the resolution of audit recommendation 1 OIG-16-001 OFAC Libyan Sanctions Case Study (Please read this correspondence in conjunction with the report.)":
    # Need to make up a report_id for this supplemental document
    report_id = "OIG-16-001-resolution"
    title = report_summary
  else:
    raise Exception("Couldn't parse report ID: %s" % repr(report_summary))

  if report_id == 'OIG-15-015' and \
      'Financial Statements for hte Fiscal Years 2014 and 2013' in title:
    # This report is listed twice, once with a typo
    return

  if report_id == 'OIG-07-003' and published_on_text == '11/23/2006':
    # This report is listed twice, once with the wrong date
    return

  # There are copy-paste errors with several retracted reports
  if report_id == 'OIG-14-037':
    if published_on.year == 2011 or published_on.year == 2010:
      return
  if report_id == 'OIG-13-021' and published_on_text == '12/12/2012':
    return

  if published_on is None:
    admin.log_no_date("treasury", report_id, title)
    return

  agency_slug_text = children[0].text

  if report_id in REPORT_AGENCY_MAP:
    agency_slug = REPORT_AGENCY_MAP[report_id]
  else:
    agency_slug = clean_text(agency_slug_text.split("&")[0]).lower()

  if (report_id in UNRELEASED_REPORTS
    or "If you would like a copy of this report" in report_summary
    or "If you would like to see a copy of this report" in report_summary
    or "have been removed from the OIG website" in report_summary
    or "removed the auditors\u2019 reports from the" in report_summary
    or "Classified Report" in report_summary
    or "Sensitive But Unclassified" in report_summary
    or "To obtain further information, please contact the OIG" in report_summary
    ):
    unreleased = True
    report_url = None
    landing_url = page_url
  else:
    link = result.select("a")[0]
    report_url = urljoin(AUDIT_REPORTS_BASE_URL, link['href'])
    if report_url == AUDIT_REPORTS_BASE_URL:
      raise Exception("Invalid link found: %s" % link)
    unreleased = False
    landing_url = None

  # HTTPS, even if they haven't updated their links yet
  if report_url is not None:
    report_url = re.sub("^http://www.treasury.gov", "https://www.treasury.gov", report_url)

  if report_url == "https://www.treasury.gov/about/organizational-structure/ig/Documents/OIG-11-071.pdf":
    report_url = "https://www.treasury.gov/about/organizational-structure/ig/Documents/OIG11071.pdf"

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'treasury',
    'inspector_url': 'https://www.treasury.gov/about/organizational-structure/ig/',
    'agency': agency_slug,
    'agency_name': AGENCY_NAMES[agency_slug],
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
  if landing_url:
    report['landing_url'] = landing_url

  return report

def report_from(result, page_url, report_type, year_range):
  try:
    title, date1, date2 = result.text.rsplit(",", 2)
    published_on_text = date1 + date2
    published_on = datetime.datetime.strptime(published_on_text.strip(), '%B %d %Y')
  except ValueError:
    try:
      title, date1, date2, date3 = result.text.rsplit(maxsplit=3)
      published_on_text = date1 + date2 + date3
      published_on = datetime.datetime.strptime(published_on_text.strip(), '%B%d,%Y')
    except ValueError:
      title = result.text
      published_on = None

  title = clean_text(title)
  original_title = title
  report_id, title = title.split(maxsplit=1)
  report_id = report_id.rstrip(":")
  if result.name == "a":
    link = result
  else:
    link = result.a

  report_url = urljoin(page_url, link['href'])

  # HTTPS, even if they haven't updated their links yet
  report_url = re.sub("^http://www.treasury.gov", "https://www.treasury.gov", report_url)

  if report_id.find('-') == -1:
    # If the first word of the text doesn't contain a hyphen,
    # then it's probably part of the title, and not a tracking number.
    # In this case, fall back to the URL.
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)
    report_id = unquote(report_id)

    # Reset the title, since we previously stripped off the first word
    # as a candidate report_id.
    title = original_title

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    admin.log_no_date("treasury", report_id, title, report_url)
    return

  # Skip this report, it already shows up under other audit reports
  if report_id == "Role of Non-Career Officials in Treasury FOIA Processing":
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'treasury',
    'inspector_url': 'https://www.treasury.gov/about/organizational-structure/ig/',
    'agency': 'treasury',
    'agency_name': "Department of the Treasury",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, page_url, year_range):
  published_on_text = clean_text(result.text)
  published_on = datetime.datetime.strptime(published_on_text.strip(), '%B %d, %Y')
  title = "Semiannual Report - {}".format(published_on_text)

  report_url = urljoin(page_url, result['href'])

  # HTTPS, even if they haven't updated their links yet
  report_url = re.sub("^http://www.treasury.gov", "https://www.treasury.gov", report_url)

  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)
  report_id = unquote(report_id)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'treasury',
    'inspector_url': 'https://www.treasury.gov/about/organizational-structure/ig/',
    'agency': 'treasury',
    'agency_name': "Department of the Treasury",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
