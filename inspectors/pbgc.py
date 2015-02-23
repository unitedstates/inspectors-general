#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.pbgc.gov/
archive = 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://oig.pbgc.gov/evaluations/{year}.html"
CONGRESSIONAL_REQUESTS_URL = "http://oig.pbgc.gov/requests.html"
SEMIANNUAL_REPORTS_URL = "http://oig.pbgc.gov/reports.html"
CONGRESSIONAL_TESTIMONY_URL = "http://oig.pbgc.gov/testimony.html"

BASE_REPORT_URL = "http://oig.pbgc.gov/"

HEADER_ROW_TEXT = [
  'Audits',
  'Evaluations',
  'Report Title',
]
PDF_REGEX = re.compile("\.pdf")

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  for year in year_range:
    if year < 1998:  # The earliest year for audit reports
      continue
    year_url = AUDIT_REPORTS_URL.format(year=year)
    doc = BeautifulSoup(utils.download(year_url))
    results = doc.select("tr")
    if not results:
      raise inspector.NoReportsFoundError("Pension Benefit Guaranty Corporation (audit reports)")
    for result in results:
      report = report_from(result, report_type='audit', year_range=year_range)
      if report:
        inspector.save_report(report)

  # Pull the congressional requests
  doc = BeautifulSoup(utils.download(CONGRESSIONAL_REQUESTS_URL))
  results = doc.select("tr")
  if not results:
    raise inspector.NoReportsFoundError("Pension Benefit Guaranty Corporation (congressional requests)")
  for result in results:
    report = report_from(result, report_type='congress', year_range=year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL))
  results =  doc.select("div.holder a")
  if not results:
    raise inspector.NoReportsFoundError("Pension Benefit Guaranty Corporation (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the congressional testimony
  doc = BeautifulSoup(utils.download(CONGRESSIONAL_TESTIMONY_URL))
  results =  doc.select("div.holder a")
  if not results:
    raise inspector.NoReportsFoundError("Pension Benefit Guaranty Corporation (congressional testimony)")
  for result in results:
    report = testimony_report_from(result, year_range)
    if report:
      inspector.save_report(report)

saved_report_urls = set()

def report_from(result, report_type, year_range):
  if len(result.select("td")) > 0:
    title = inspector.sanitize(result.select("td")[0].text)
  else:
    return

  if (not title) or (title in HEADER_ROW_TEXT):
    # Skip the header rows
    return

  report_id = result.select("td")[1].text.replace("/", "-").replace(" ", "-")
  if report_id == "N-A":
    report_id = result.select("td")[0].text.replace("/", "-").replace(" ", "-")

  published_on_text = result.select("td")[2].text
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
  except ValueError:
    published_on = datetime.datetime.strptime(published_on_text, '%m/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  unreleased = False
  link = result.find("a")
  landing_url = urljoin(BASE_REPORT_URL, link.get('href'))
  if landing_url.endswith(".pdf"):
    # Inline report
    report_url = landing_url
    landing_url = None
    summary = None
  else:
    landing_page = BeautifulSoup(utils.download(landing_url))
    summary = " ".join(landing_page.select("div.holder")[0].text.split())
    report_link = landing_page.find("a", href=PDF_REGEX)
    if report_link:
      report_url = urljoin(landing_url, report_link.get('href'))
    else:
      unreleased = True
      report_url = None

  if report_url:
    # OIG MAR-2012-10/PA-12-87 is posted under both Audits/Evaluations/MARs and
    # Congressional Requests.
    if report_url in saved_report_urls:
      return
    saved_report_urls.add(report_url)

  report = {
    'inspector': "pbgc",
    'inspector_url': "http://oig.pbgc.gov",
    'agency': "pbgc",
    'agency_name': "Pension Benefit Guaranty Corporation",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if summary:
    report['summary'] = summary
  if unreleased:
    report['unreleased'] = unreleased
  if landing_url:
    report['landing_url'] = landing_url
  return report

def semiannual_report_from(result, year_range):
  # This will look like "toggleReport('SARC-47-49');" and we want to pull out
  # the SARC-47-49
  report_id_javascript = result.get('onclick')
  report_id = re.search("'(.*)'", report_id_javascript).groups()[0]
  landing_url  = "http://oig.pbgc.gov/sarc/{report_id}.html".format(report_id=report_id)
  landing_page = BeautifulSoup(utils.download(landing_url))

  title = " ".join(landing_page.select("h3")[0].text.split())
  relative_report_url = landing_page.find("a", text="Read Full Report").get('href')

  # The relative report urls try to go up a level too many. Most browsers seem
  # to just ignore this so we will too.
  relative_report_url = relative_report_url.replace("../", "", 1)
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, relative_report_url)

  # There is probably a way to be a bit smarter about this
  summary = landing_page.text.strip()

  published_on_text = title.rsplit("-")[-1].rsplit("through")[-1].replace(".", "").strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  report = {
    'inspector': "pbgc",
    'inspector_url': "http://oig.pbgc.gov",
    'agency': "pbgc",
    'agency_name': "Pension Benefit Guaranty Corporation",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if summary:
    report['summary'] = summary
  if landing_url:
    report['landing_url'] = landing_url
  return report

def testimony_report_from(result, year_range):
  title = result.text
  report_url = urljoin(BASE_REPORT_URL, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  published_on_text = "-".join(re.search('\((\w+) (\d+), (\d{4})\)', result.text).groups())
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%b-%d-%Y')
  except ValueError:
    published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  report = {
    'inspector': "pbgc",
    'inspector_url': "http://oig.pbgc.gov",
    'agency': "pbgc",
    'agency_name': "Pension Benefit Guaranty Corporation",
    'type': 'testimony',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
