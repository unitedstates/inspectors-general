#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.tva.gov
# Oldest report: 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://oig.tva.gov/reports/{year}.html"
SEMIANNUAL_REPORTS_URL = "http://oig.tva.gov/reports/oig-reports.xml"

PDF_REPORT_FORMAT = "http://oig.tva.gov/reports/node/semi/{report_number}/semi{report_number}.pdf"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for year in year_range:
    if year < 2005:  # This is the earliest audits go back
      continue
    url = AUDIT_REPORTS_URL.format(year=year)
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("div.content")
    for result in results:
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL))
  results = doc.select("report")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, landing_url, year_range):
  header = result.find_previous("p", class_="heading")

  published_on_text, title, report_id = header.text.split("-", 2)
  title = title.strip()
  report_id = report_id.strip().replace("/", "-")

  if "summary only" in result.text.lower():
    unreleased = True
    report_url = None
  else:
    unreleased = False
    report_url = urljoin(landing_url, result.find("a").get('href'))

  # Skip the last 'p' since it is just the report link
  summary_text = [paragraph.text for paragraph in result.findAll("p")[:-1]]
  summary = "\n".join(summary_text)

  # Some reports list multiple dates. Split on '&' to get the latter.
  published_on_text = published_on_text.split("&")[-1].strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'tva',
    'inspector_url': 'http://oig.tva.gov',
    'agency': 'tva',
    'agency_name': 'Tennessee Valley Authority',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'summary': summary,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

def semiannual_report_from(result, year_range):
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result.get('pdfurl'))
  if report_url.endswith("index.html"):
    # Sometime they link to the landing page instead of the report. We convert
    # the url to get the actual report.
    report_number = report_url.split("/")[-2]
    report_url = PDF_REPORT_FORMAT.format(report_number=report_number)

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  published_on_text = result.find("date").text
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Semiannual Report {}".format(published_on_text)
  alternative_title = result.find("title").text.strip()
  if alternative_title:
    title = "{} ({})".format(alternative_title, title)
  summary = result.find("summary").text.strip()

  report = {
    'inspector': 'tva',
    'inspector_url': 'http://oig.tva.gov',
    'agency': 'tva',
    'agency_name': 'Tennessee Valley Authority',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'summary': summary,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
