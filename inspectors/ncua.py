#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.ncua.gov/about/Leadership/Pages/page_oig.aspx
# Oldest report: 1999

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.ncua.gov/about/Leadership/CO/OIG/Pages/AuditRpt{year}.aspx"
SEMIANNUAL_REPORTS_URL = "http://www.ncua.gov/about/Leadership/CO/OIG/Pages/SemiAnnRpts.aspx"
FOIA_REPORTS_URL = "http://www.ncua.gov/about/Leadership/CO/OIG/Pages/FOIA2012.aspx"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for year in year_range:
    if year < 2002:  # The oldest page for audit reports
      continue
    doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL.format(year=year)))
    results = doc.select("div.content table tr")
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

  # Pull the FOIA reports
  doc = BeautifulSoup(utils.download(FOIA_REPORTS_URL))
  results = doc.select("div.content table tr")
  for index, result in enumerate(results):
    if not index:
      # Skip the header row
      continue
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL))
  results = doc.select("div.content a")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def clean_text(text):
  # This character is not technically whitespace so we have to manually replace it
  return text.replace("\u200b", " ").strip()

def report_from(result, year_range):
  link = result.find("a")
  report_id = "-".join(link.text.replace("/", "-").replace("'", "").split())
  report_url = urljoin(AUDIT_REPORTS_URL, link.get('href'))
  try:
    title = clean_text(result.select("td")[1].text)
  except IndexError:
    title = clean_text(result.select("td")[0].text)

  published_on_text = clean_text(result.select("td")[-1].text)
  published_on_text = published_on_text.replace("//", "/")  # Some accidental double slashes
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "ncua",
    'inspector_url': "http://www.ncua.gov/about/Leadership/Pages/page_oig.aspx",
    'agency': "ncua",
    'agency_name': "National Credit Union Administration",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, year_range):
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  title = result.text

  # This normalization will make later processing easier
  published_on_text = title.replace(" thru ", " - ")

  try:
    published_on_text = "-".join(re.search('(\w+) (\d+), (\d{4})', published_on_text).groups())
    published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')
  except AttributeError:
    published_on_text = published_on_text.split("-")[-1].split("–")[-1].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "ncua",
    'inspector_url': "http://www.ncua.gov/about/Leadership/Pages/page_oig.aspx",
    'agency': "ncua",
    'agency_name': "National Credit Union Administration",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
