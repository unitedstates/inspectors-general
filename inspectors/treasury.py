#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin, unquote

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.treasury.gov/about/organizational-structure/ig/Pages/audit_reports_index.aspx
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add an agency for report 'OIG-09-015' listed on
# http://www.treasury.gov/about/organizational-structure/ig/Pages/by-date-2009.aspx
# - There is an extra tr.ms-rteTableEvenRow-default at the end of
# http://www.treasury.gov/about/organizational-structure/ig/Pages/by-date-2014.aspx
# - Add published dates for all reports at
# http://www.treasury.gov/about/organizational-structure/ig/Pages/other-reports.aspx

AUDIT_REPORTS_BASE_URL = "http://www.treasury.gov/about/organizational-structure/ig/Pages/by-date-{}.aspx"
TESTIMONIES_URL = "http://www.treasury.gov/about/organizational-structure/ig/Pages/testimony_index.aspx"
PEER_AUDITS_URL = "http://www.treasury.gov/about/organizational-structure/ig/Pages/peer_audit_reports_index.aspx"
OTHER_REPORTS_URL = "http://www.treasury.gov/about/organizational-structure/ig/Pages/other-reports.aspx"
SEMIANNUAL_REPORTS_URL = "http://www.treasury.gov/about/organizational-structure/ig/Pages/semiannual_reports_index.aspx"

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
  "IGATI",
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
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for year in year_range:
    if year < 2006:  # This is the oldest year for these reports
      year = 2006
    url = AUDIT_REPORTS_BASE_URL.format(year)
    doc = beautifulsoup_from_url(url)
    results = []
    results.extend(doc.select("tr.ms-rteTableOddRow-default"))
    results.extend(doc.select("tr.ms-rteTableEvenRow-default"))
    for result in results:
      report = audit_report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

  for report_type, url in OTHER_URLS.items():
    doc = beautifulsoup_from_url(url)
    results = doc.select("#ctl00_PlaceHolderMain_ctl05_ctl01__ControlWrapper_RichHtmlField > p > a")
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

  doc = beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("#ctl00_PlaceHolderMain_ctl05_ctl01__ControlWrapper_RichHtmlField > p > a")
  for result in results:
    report = semiannual_report_from(result, SEMIANNUAL_REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

def clean_text(text):
  # A lot of text on this page has extra characters
  return text.replace('\u200b', '').replace('\ufffd', ' ').replace('\xa0', ' ').strip()

def audit_report_from(result, page_url, year_range):
  published_on_text = clean_text(result.select("td")[1].text)

  # this is the header row
  if published_on_text.strip() == "Date":
    return None

  date_formats = ['%m/%d/%Y', '%m/%d%Y']
  for date_format in date_formats:
    try:
      published_on = datetime.datetime.strptime(published_on_text, date_format)
    except ValueError:
      pass

  report_summary = clean_text(result.select("td")[2].text)
  if not report_summary:
    # There is an extra row that we want to skip
    return

  report_id, title = report_summary.split(maxsplit=1)
  report_id = report_id.rstrip(":")

  if report_id in REPORT_AGENCY_MAP:
    agency_slug = REPORT_AGENCY_MAP[report_id]
  else:
    agency_slug = clean_text(result.select("td")[0].text.split("&")[0]).lower()

  if (report_id in UNRELEASED_REPORTS
    or "If you would like a copy of this report" in title
    or "If you would like to see a copy of this report" in title
    ):
    unreleased = True
    report_url = None
    landing_url = page_url
  else:
    link = result.select("a")[0]
    report_url = urljoin(AUDIT_REPORTS_BASE_URL, link.get('href'))
    unreleased = False
    landing_url = None

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'treasury',
    'inspector_url': 'http://www.treasury.gov/about/organizational-structure/ig/',
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
  report_id, title = title.split(maxsplit=1)
  report_id = report_id.rstrip(":")
  report_url = urljoin(page_url, result.get('href'))

  if report_id.find('-') == -1:
    # If the first word of the text doesn't contain a hyphen,
    # then it's probably part of the title, and not a tracking number.
    # In this case, fall back to the URL.
    print("before", report_id)
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)
    report_id = unquote(report_id)
    print("after", report_id)

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'treasury',
    'inspector_url': 'http://www.treasury.gov/about/organizational-structure/ig/',
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

  report_url = urljoin(page_url, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)
  report_id = unquote(report_id)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'treasury',
    'inspector_url': 'http://www.treasury.gov/about/organizational-structure/ig/',
    'agency': 'treasury',
    'agency_name': "Department of the Treasury",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None