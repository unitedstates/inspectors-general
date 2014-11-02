#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www2.ed.gov/about/offices/list/oig/areports.html
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#   report_id: limit to a single report
#
# Notes for IG's web team:
# - Fix the row for A17C0008 on
# http://www2.ed.gov/about/offices/list/oig/areports2003.html
# - Fix the published date for A06K0003
# on http://www2.ed.gov/about/offices/list/oig/areports2011.html
# - Multiple reports on http://www2.ed.gov/about/offices/list/oig/ireports.html
# say that they were published in 'Decemver' or 'Deccember' instead of 'December'

AUDIT_REPORTS_URL = "https://www2.ed.gov/about/offices/list/oig/areports{}.html"
SEMIANNUAL_REPORTS_URL = "https://www2.ed.gov/about/offices/list/oig/sarpages.html"

INSPECTION_REPORTS_URL = "https://www2.ed.gov/about/offices/list/oig/aireports.html"
INVESTIGATIVE_REPORTS_URL = "https://www2.ed.gov/about/offices/list/oig/ireports.html"
CONGRESSIONAL_TESTIMONY_URL = "https://www2.ed.gov/about/offices/list/oig/testimon.html"
SPECIAL_REPORTS_URL = "https://www2.ed.gov/about/offices/list/oig/specialreportstocongress.html"
OTHER_REPORTS_URL = "https://www2.ed.gov/about/offices/list/oig/otheroigproducts.html"

OTHER_REPORTS_URL = {
  "other": OTHER_REPORTS_URL,
  "other": SPECIAL_REPORTS_URL,
  "testimony": CONGRESSIONAL_TESTIMONY_URL,
  "investigation": INVESTIGATIVE_REPORTS_URL,
  "inspection": INSPECTION_REPORTS_URL,
}

REPORT_PUBLISHED_MAP = {
  "statelocal032002": datetime.datetime(2002, 3, 21),
  "statloc082001": datetime.datetime(2001, 8, 3),
  "A17B0006": datetime.datetime(2002, 2, 27),
  "A17A0002": datetime.datetime(2001, 2, 28),
  "A1790019": datetime.datetime(2000, 2, 28),  # Approximation
  "A17C0008": datetime.datetime(2003, 1, 31),
  "PESMemo": datetime.datetime(2001, 1, 1),  # Approximation
  "s1370001": datetime.datetime(1999, 3, 18),
  "oigqualitystandardsforalternativeproducts": datetime.datetime(2010, 3, 11),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # optional: limit to a single report
  report_id = options.get("report_id")

  # Get the audit reports
  pre_1998_audit_flag = False
  for year in year_range:
    if year <= 1998:
      if pre_1998_audit_flag:
        continue
      else:
        pre_1998_audit_flag = True
    url = audit_url_for(year)
    doc = beautifulsoup_from_url(url)
    agency_tables = doc.find_all("table", {"border": 1})
    for agency_table in agency_tables:
      results = agency_table.select("tr")
      for index, result in enumerate(results):
        if not index:
          # First row is the header
          continue
        report = audit_report_from(result, url, year_range)
        if report:
          # optional: filter to a single report
          if report_id and (report_id != report['report_id']):
            continue

          inspector.save_report(report)

  # Get semiannual reports
  doc = beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  table = doc.find("table", {"border": 1})
  for index, result in enumerate(table.select("tr")):
    if index < 2:
      # The first two rows are headers
      continue
    report = semiannual_report_from(result, SEMIANNUAL_REPORTS_URL, year_range)
    if report:
      # optional: filter to a single report
      if report_id and (report_id != report['report_id']):
        continue
      inspector.save_report(report)

  # Get other reports
  for report_type, url in OTHER_REPORTS_URL.items():
    doc = beautifulsoup_from_url(url)
    results = doc.select("div.contentText ul li")
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        # optional: filter to a single report
        if report_id and (report_id != report['report_id']):
          continue

        inspector.save_report(report)

audit_reports_seen = set()

def audit_report_from(result, page_url, year_range):
  if not result.text.strip():
    # Just an empty row
    return

  title = result.select("td")[0].text.strip()
  report_url = urljoin(page_url, result.select("td a")[0].get('href'))

  report_id = None
  if len(result.select("td")) != 3:
    report_id = result.select("td")[1].text.strip()
    if report_id.startswith("ACN: "):
      report_id = report_id[5:]
  if not report_id:
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    # See notes to the IG Web team for some of this
    published_on_text = result.select("td")[2].text.strip().replace(")", "").replace("//", "/")
    date_formats = ['%m/%d/%Y', '%m/%d/%y', '%m/%Y']
    published_on = None
    for date_format in date_formats:
      try:
        published_on = datetime.datetime.strptime(published_on_text, date_format)
      except ValueError:
        pass

  # The following report is linked to twice from the IG's website, once with
  # the date 02/06/2003 (correct) and once with the date 02/06/2002. Both links
  # point to the same PDF file, have the same title, and have the same ACN.
  # If we are processing the duplicate entry, suppress it.
  if report_id == "A17D0002" and published_on.year == 2002 and published_on.month == 2 and published_on.day == 6:
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  key = (report_id, title, report_url)
  if key in audit_reports_seen:
    return
  audit_reports_seen.add(key)

  report = {
    'inspector': 'education',
    'inspector_url': 'https://www2.ed.gov/about/offices/list/oig/',
    'agency': 'education',
    'agency_name': "Department of Education",
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def audit_url_for(year):
  if year < 1998:
    # This is the first listed year
    year = 1998

  if year == 2001:
    # This one needs a capital A. Yup.
    return "https://www2.ed.gov/about/offices/list/oig/Areports2001.html"

  if year == datetime.datetime.today().year:
    # The current year is on the main page
    return AUDIT_REPORTS_URL.format("")
  else:
    return AUDIT_REPORTS_URL.format(year)

def semiannual_report_from(result, page_url, year_range):
  report_url = urljoin(page_url, result.select("a")[0].get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)
  date_range_text = result.select("td")[1].text
  title = "Semiannual Report - {}".format(date_range_text)
  published_on_text = date_range_text.split("-")[-1].strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  report = {
    'inspector': 'education',
    'inspector_url': 'https://www2.ed.gov/about/offices/list/oig/',
    'agency': 'education',
    'agency_name': "Department of Education",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def report_from(result, url, report_type, year_range):
  report_url = urljoin(url, result.select("a")[0].get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  title = result.text.split(" ACN:")[0]
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    result_text = result.text.replace(",", "").replace("\n", " ")
    result_text = " ".join(result_text.split())  # Remove any double spaces
    result_text = result_text.replace("Decemver", "December").replace("Deccember", "December")  # See note to IG Web team
    try:
      published_on_text = "/".join(re.search("(\d+)/(\d+)/(\d+)", result_text).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
    except AttributeError:
      try:
        published_on_text = "/".join(re.search("(\d+)/(\d+)", result_text).groups())
        published_on = datetime.datetime.strptime(published_on_text, '%m/%Y')
      except AttributeError:
        try:
          published_on_text = "/".join(re.search("(\w+) (\d+) (\d+)", result_text).groups())
          published_on = datetime.datetime.strptime(published_on_text, '%B/%d/%Y')
        except AttributeError:
          published_on_text = "/".join(re.search("(\w+) (\d+)", result_text).groups())
          published_on = datetime.datetime.strptime(published_on_text, '%B/%Y')

  if "thestartingline.ed.gov" in report_url:
    return None

  report = {
    'inspector': 'education',
    'inspector_url': 'https://www2.ed.gov/about/offices/list/oig/',
    'agency': 'education',
    'agency_name': "Department of Education",
    'type': report_type,
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
