#!/usr/bin/env python

import datetime
import logging
import os
import time

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.va.gov/oig/apps/info/OversightReports.aspx
archive = 1996

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.va.gov/oig/apps/info/OversightReports.aspx"
SEMIANNUAL_REPORTS_URL = "http://www.va.gov/oig/publications/semiannual-reports.asp"

AGENCY_SLUG_MAP = {
  "Department of Veterans Affairs": "VA",
  "Veterans Health Administration": "VHA",
  "Veterans Benefits Administration": "VBA",
  "National Cemetery Administration": "NCA",
  "Office of General Counsel": "OGC",
  "Office of Acquisitions, Logistics, and Construction": "OALC",
  "Office of Information and Technology": "OIT",
  "Office of Congressional and Legislative Affairs": "OCLA",
  "Office of Human Resources and Administration": "OHRA",
  "Office of Management": "OM",
  "Office of Operations, Security & Preparedness": "OOSP",
  "Office of Policy and Planning": "OPP",
  "Office of Public and Intergovernmental Affairs": "OPIA",
  "Board of Veterans' Appeals": "BVA",
  "Center for Minority Veterans": "CMV",
  "Center for Women Veterans": "CWM",
  "Office of Employment Discrimination Complaint Adjudication": "OEDCA",
  "Office of Small & Disadvantaged Business Utilization": "OSDBU",
  "Office of Advisory Committee Management": "OACM",
  "Center for Faith-Based and Neighborhood Partnerships": "CFNP",
  "Office of Federal Recovery Coordination": "OFRC",
  "Office of Non-Governmental Organization Gateway Initiative": "ONOGI",
  "Office of Survivors Assistance": "OSA",
  "Office of Veterans Service Organizations Liaison": "OVSOL",
}

MAX_ATTEMPTS = 5
ERROR_PAGE_TEXT = 'This report summary cannnot be displayed at this time.'

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for page in range(1, 1000):
    doc = beautifulsoup_from_url("{}?RS={}".format(REPORTS_URL, page))
    results = doc.select("div.leadin")
    if not results:
      break
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

  # Pull the semiannual reports
  doc = beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("div.leadin")
  for result in results:
    report = semiannual_report_from(result, year_range)
    inspector.save_report(report)

def report_type_from_topic(topic):
  if "Audit" in topic or topic in ["CAP Reviews", "CBOC Reports"]:
    return 'audit'
  elif 'Inspection' in topic:
    return 'inspection'
  elif 'Investigation' in topic:
    return 'investigation'
  elif 'FISMA Report' in topic:
    return 'fisma'
  else:
    return 'other'

def report_from(result, year_range):
  link = result.select("a")[0]
  title = link.text
  landing_url = result.select("p.summary a")[0].get('href')
  published_on_text = result.select("p.summary")[0].text.split("|")[0].strip()
  published_on = datetime.datetime.strptime(published_on_text, "%m/%d/%Y")

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  # These pages occassionally return text indicating there was a temporary
  # error so we will retry if necessary.
  for attempt in range(MAX_ATTEMPTS):
    landing_page = beautifulsoup_from_url(landing_url)
    page_text = landing_page.select("div.report-summary")[0].text.strip()
    if page_text != ERROR_PAGE_TEXT:
      break
    time.sleep(3)
  if attempt == MAX_ATTEMPTS - 1:
    raise Exception("Could not retrieve url %s", landing_url)

  field_mapping = {}
  for field in landing_page.select("div.report-summary tr"):
    field_name = field.select("th")[0].text.rstrip(":")
    field_value = field.select("td")[0].text
    field_mapping[field_name] = field_value

  button_results = landing_page.select("div.big-green-button a")
  if len(button_results) == 1:
    report_url = button_results[0].get("href")
  else:
    report_url = None

  report_id = field_mapping['Report Number']
  topic = field_mapping['Report Type']
  report_type = report_type_from_topic(topic)
  summary = field_mapping['Summary']
  location = field_mapping['City/State']
  report_author = field_mapping['Report Author']
  agency_name = field_mapping['VA Office']
  if not agency_name:
    agency_name = 'Department of Veterans Affairs'

  agency_slug = None
  for name in AGENCY_SLUG_MAP:
    if name in agency_name:
      agency_slug = AGENCY_SLUG_MAP[name]
      break

  release_type = field_mapping['Release Type']
  unreleased = (release_type == "Restricted")
  report = {
    'inspector': 'va',
    'inspector_url': 'http://www.va.gov/oig',
    'agency': agency_slug,
    'agency_name': agency_name,
    'report_id': report_id,
    'url': report_url,
    'landing_url': landing_url,
    'type': report_type,
    'topic': topic,
    'summary': summary,
    'title': title,
    'author': report_author,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = True
  if location:
    report['location'] = location
  return report

def semiannual_report_from(result, year_range):
  report_url = result.select("a")[0].get('href')
  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]
  summary = result.select("p")[0].text
  title = result.select("h4 > a")[0].text
  try:
    published_on = datetime.datetime.strptime(title.split("-")[-1].strip(), '%B %d, %Y')
  except ValueError:
    published_on = datetime.datetime.strptime(title.split(" to ")[-1].strip(), '%B %d, %Y')

  report = {
    'inspector': 'va',
    'inspector_url': 'http://www.va.gov/oig',
    'agency': 'VA',
    'agency_name': "Department of Veterans Affairs",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'topic': "Semiannual Report",
    'summary': summary,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None
