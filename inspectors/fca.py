#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www.fca.gov/home/inspector.html
archive = 1989

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "https://www.fca.gov/home/inspector/ig_reports.html"
REPORT_ARCHIVE_URL = "https://www.fca.gov/home/inspector/oigarchive.html"
SEMIANNUAL_REPORTS_URL = "https://www.fca.gov/home/inspector/semiannual.html"

REPORT_PUBLISHED_MAPPING = {
  "RegulatoryDevelopmentSurvey2002": datetime.datetime(2002, 10, 22),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the general reports
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  results = doc.select("div#mainContent li.mainContenttext a")
  for result in results:
    report = report_from(result, REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

  # Pull the archive reports
  doc = BeautifulSoup(utils.download(REPORT_ARCHIVE_URL))
  results = doc.select("div#mainContent li.mainContenttext a") + doc.select("div#mainContent span.mainContenttext a")
  for result in results:
    if not result.text:
      continue
    report = report_from(result, REPORT_ARCHIVE_URL, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = BeautifulSoup(utils.download(SEMIANNUAL_REPORTS_URL))
  results = doc.select("div#mainContent li.mainContenttext a")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def clean_text(text):
  return text.replace("Â\xa0", " ").strip()

def type_for_report(text):
  if "Audit" in text:
    return "audit"
  elif "Semiannual Report" in text:
    return "semiannual_report"
  elif "Inspection" in text:
    return "inspection"
  elif "FISMA" in text:
    return "fisma"
  elif "Peer Review" in text:
    return "peer_review"
  elif "Survey" in text:
    return "research"
  elif "Performance" in text:
    return "performance"
  else:
    return "other"

def report_from(result, landing_url, year_range):
  report_url = urljoin(landing_url, result.get('href'))

  if landing_url + '#' in report_url:
    # These are just anchor links, skip them.
    return

  if result.find_parent("ul") and result.find_parent("ul").get('type') == 'disc':
    # These are just anchor links, skip them.
    return

  title = clean_text(result.text)

  if title == 'Inspector General Reports':
    # Just a return link to the main IG page
    return

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  estimated_date = False
  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    try:
      published_on_text = result.parent.contents[1].lstrip(",").split("(")[0].strip()
    except (IndexError, TypeError):
      published_on_text = result.text.strip()
    published_on_text = clean_text(published_on_text)

    try:
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except ValueError:
      try:
        published_on_text = "/".join(re.search("(\w{3}).* (\d{4})", published_on_text).groups())
        published_on = datetime.datetime.strptime(published_on_text, '%b/%Y')
      except AttributeError:
        # For reports where we can only find the year, set them to Nov 1st of that year
        try:
          published_on_year = int(re.search("FYs?\s*(\d{4})", title).groups()[0])
        except AttributeError:
          published_on_year = int(title.split()[0])
        published_on = datetime.datetime(published_on_year, 11, 1)
        estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report_type_text = result.find_previous("p", class_="mainContentheader2").text.strip()
  report_type = type_for_report(report_type_text)

  report = {
    'inspector': 'fca',
    'inspector_url': 'https://www.fca.gov/home/inspector.html',
    'agency': 'fca',
    'agency_name': 'Farm Credit Administration',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

def semiannual_report_from(result, year_range):
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  published_on_text = result.text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  title = "Semiannual Report {}".format(published_on_text)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fca',
    'inspector_url': 'https://www.fca.gov/home/inspector.html',
    'agency': 'fca',
    'agency_name': 'Farm Credit Administration',
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
