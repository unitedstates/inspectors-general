#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector

# http://www.nrc.gov/insp-gen.html
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - There are a few report pages which don't list published dates. See
# REPORT_PUBLISHED_MAPPING

AUDIT_REPORTS_URL = "http://www.nrc.gov/reading-rm/doc-collections/insp-gen/{}/"
ARCHIVED_REPORTS_URL = "http://www.nrc.gov/reading-rm/doc-collections/insp-gen/archived.html"
PRIOR_PENDING_REPORTS_URL = "http://www.nrc.gov/reading-rm/doc-collections/insp-gen/prior-pending.html"
SEMIANNUAL_REPORTS_URL = "http://www.nrc.gov/reading-rm/doc-collections/nuregs/staff/sr1415/index.html"
OTHER_REPORT_URLS = [
  # These brochures have been taken off of the website as of April 7, 2015
  #  ("http://www.nrc.gov/reading-rm/doc-collections/nuregs/brochures/br0304/",
  #   "NUREG-BR-0304-"),
  #  ("http://www.nrc.gov/reading-rm/doc-collections/nuregs/brochures/br0272/",
  #   "NUREG-BR-0272-")
]

BASE_REPORT_URL = "http://www.nrc.gov"

UNRELEASED_TEXTS = [
  "not for public release",
  "not for release",
  "sensitive security information",
  "security related information",
  "for information call oig",
]

REPORT_PUBLISHED_MAPPING = {
  "1415v14n1": datetime.datetime(2001, 9, 30),
  "v14n2": datetime.datetime(2002, 3, 31),
}

PDF_REGEX = re.compile("pdf")


def run(options):
  year_range = inspector.year_range(options, archive)

  urls = [ARCHIVED_REPORTS_URL, PRIOR_PENDING_REPORTS_URL]
  for year in year_range:
    if year >= 2005:
        urls.append(AUDIT_REPORTS_URL.format(year))

  # Pull the audit reports
  for url in urls:
    doc = utils.beautifulsoup_from_url(url)
    results = doc.find("table", border="1").select("tr")
    if not results:
      raise inspector.NoReportsFoundError("Nuclear Regulatory Commission (%d)" % year)
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = audit_report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

  # Pull the congressional testimony
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  semiannual_reports_table = doc.find("table", border="1")
  results = semiannual_reports_table.select("tr")
  if not results:
    raise inspector.NoReportsFoundError("Nuclear Regulatory Commission (congressional testimony)")
  for index, result in enumerate(results):
    if index < 2:
      # Skip the first two header rows
      continue
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the other reports
  for reports_url, id_prefix in OTHER_REPORT_URLS:
    doc = utils.beautifulsoup_from_url(reports_url)
    results = doc.find("table", border="1").select("tr")
    if not results:
      raise inspector.NoReportsFoundError("Nuclear Regulatory Commission (other)")
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = other_report_from(result, year_range, id_prefix, reports_url)
      if report:
        inspector.save_report(report)


def audit_report_from(result, landing_url, year_range):
  title = " ".join(result.contents[1].text.split())

  unreleased = False
  file_type = None
  report_link = result.find("a")
  try:
    report_url = urljoin(landing_url, report_link.get('href'))
  except AttributeError as exc:
    for unreleased_text in UNRELEASED_TEXTS:
      if unreleased_text in title.lower():
        unreleased = True
        report_url = None
    if not unreleased:
      raise exc

  if not unreleased:
    landing_url = None
    if not report_url.endswith(".pdf"):
      file_type = 'html'

  try:
    report_id = result.select("td")[2].text
  except IndexError:
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)

  if report_url and os.path.splitext(report_url)[0].endswith("fin"):
    report_id = report_id + "-final"

  try:
    published_on_text = result.contents[3].text
  except IndexError:
    # This can be in different spots depending on the row
    published_on_text = result.contents[-2].text
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nrc',
    'inspector_url': 'http://www.nrc.gov/insp-gen.html',
    'agency': 'nrc',
    'agency_name': 'Nuclear Regulatory Commission',
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
  if file_type:
    report['file_type'] = file_type
  return report


def semiannual_report_from(result, year_range):
  report_link = result.find("a")
  landing_url = urljoin(SEMIANNUAL_REPORTS_URL, report_link.get('href'))

  landing_page = utils.beautifulsoup_from_url(landing_url)
  title = " ".join(landing_page.select("#mainSubFull h1")[0].text.split())

  try:
    relative_report_url = landing_page.find(href=PDF_REGEX).get('href')
  except AttributeError:
    # Some of these reports are published as HTML on the landing page
    # Ex. http://www.nrc.gov/reading-rm/doc-collections/nuregs/staff/sr1415/v17n2/
    relative_report_url = landing_url

  file_type = None
  report_url = urljoin(landing_url, relative_report_url)
  report_filename = report_url.split("/")[-1]
  if report_filename:
    report_id, extension = os.path.splitext(report_filename)
  else:
    # HTML page with trailing slash. (http://www.nrc.gov/reading-rm/doc-collections/nuregs/staff/sr1415/v17n2/)
    report_id = report_url.split("/")[-2]
    file_type = '.html'

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    # The location of the publication date moves around too much so we search
    # the entire page
    published_on_text = " ".join(re.search("Date Published:\s+(\w+),*\s+(\d{4})", landing_page.text).groups())
    published_on = datetime.datetime.strptime(published_on_text.strip(), '%B %Y')

  report_id = "NUREG-1415-{}".format(report_id)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nrc',
    'inspector_url': 'http://www.nrc.gov/insp-gen.html',
    'agency': 'nrc',
    'agency_name': 'Nuclear Regulatory Commission',
    'type': 'semiannual_report',
    'landing_url': landing_url,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if file_type:
    report['file_type'] = file_type
  return report


def other_report_from(result, year_range, id_prefix, index_url):
  report_link = result.find("a")
  report_url = urljoin(index_url, report_link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)
  report_id = id_prefix + report_id

  volume_text = result.select("td")[0].text.strip()
  title = "OIG Fraud Bulletin/Information Digest - {}".format(volume_text)

  published_on_text = result.select("td")[1].text.split("(")[0].strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nrc',
    'inspector_url': 'http://www.nrc.gov/insp-gen.html',
    'agency': 'nrc',
    'agency_name': 'Nuclear Regulatory Commission',
    'type': 'other',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
