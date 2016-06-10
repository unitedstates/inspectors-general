#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://www.ncua.gov/About/Pages/inspector-general.aspx
archive = 1999

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

HOMEPAGE_URL = "https://www.ncua.gov/About/Pages/inspector-general.aspx"
AUDIT_REPORTS_URL = "https://www.ncua.gov/About/Pages/inspector-general/audit-reports/{year}.aspx"
SEMIANNUAL_REPORTS_URL = "https://www.ncua.gov/About/Pages/inspector-general/semiannual-reports.aspx"
OTHER_REPORTS_URL = "https://www.ncua.gov/About/Pages/inspector-general/other-reports.aspx"
PLANS_URL = "https://www.ncua.gov/About/Pages/inspector-general/performance-strategic-plans.aspx"
# Note: There is no need to scrape the "Material Loss Reviews" page, since
# these reports are included with the audit reports for each year.


def run(options):
  year_range = inspector.year_range(options, archive)
  results_flag = False

  # Pull the audit reports
  for year in year_range:
    if year < 2002:  # The oldest page for audit reports
      continue
    doc = utils.beautifulsoup_from_url(AUDIT_REPORTS_URL.format(year=year))

    if doc == None:
      # Next year's audit page may not be published yet
      continue

    results = doc.select("div.mainCenter table tr")
    if results:
      results_flag = True
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = report_from(result, report_type='audit', year_range=year_range)
      if report:
        inspector.save_report(report)

  if not results_flag:
    raise inspector.NoReportsFoundError("NCUA (audit reports)")

  # Pull the other reports
  doc = utils.beautifulsoup_from_url(OTHER_REPORTS_URL)
  results = doc.select("div.mainCenter p")
  if not results:
    raise inspector.NoReportsFoundError("NCUA (other)")
  for result in results:
    report = other_report_from(result, year_range=year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("div#mainColumns div.mainCenter a")
  if not results:
    raise inspector.NoReportsFoundError("NCUA (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the performance and strategic plans
  doc = utils.beautifulsoup_from_url(PLANS_URL)
  results = doc.select("div.mainCenter p")
  if not results:
    raise inspector.NoReportsFoundError("NCUA (performance/strategic plans)")
  for result in results:
    report = plan_from(result, year_range)
    if report:
      inspector.save_report(report)

def clean_text(text):
  return re.sub("[ \n]+", " ", inspector.sanitize(text))

def report_from(result, report_type, year_range):
  links = result.select("a[href]")
  if len(links) == 1:
    link = links[0]
  else:
    raise Exception("Found multiple links in one row\n%s" % links)
  report_id = clean_text("-".join(link.text.replace("/", "-").replace("'", "").replace(":", "").split()))
  report_url = urljoin(AUDIT_REPORTS_URL, link.get('href'))
  title = clean_text(result.select("td")[1].text)

  published_on_text = clean_text(result.select("td")[-1].text)
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "ncua",
    'inspector_url': HOMEPAGE_URL,
    'agency': "ncua",
    'agency_name': "National Credit Union Administration",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report


OTHER_REPORT_RE = re.compile("^ *(.+) +((?:January|February|Feb\\.|March|April|May|June|July|August|September|October|November|December) [0-3]?[0-9], 20[0-9][0-9]) *$")


def other_report_from(result, year_range):
  link = result.find("a")
  basename = os.path.splitext(os.path.basename(link["href"]))[0]
  report_id = clean_text(basename).replace("'", "").replace(":", "")
  report_id = re.sub("-+", "-", report_id)
  report_url = urljoin(OTHER_REPORTS_URL, link["href"])

  match = OTHER_REPORT_RE.match(clean_text(link.text))
  title = match.group(1)
  published_on_text = match.group(2)
  published_on = None
  try:
    published_on = datetime.datetime.strptime(published_on_text, "%B %d, %Y")
  except ValueError:
    pass
  if not published_on:
    try:
      published_on = datetime.datetime.strptime(published_on_text, "%b. %d, %Y")
    except ValueError:
      pass
  if not published_on:
    admin.log_no_date("ncua", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "ncua",
    'inspector_url': HOMEPAGE_URL,
    'agency': "ncua",
    'agency_name': "National Credit Union Administration",
    'type': "other",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, year_range):
  title = clean_text(result.text)
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result['href'])
  report_filename = os.path.basename(report_url)
  report_id, _ = os.path.splitext(report_filename)

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
    'inspector_url': HOMEPAGE_URL,
    'agency': "ncua",
    'agency_name': "National Credit Union Administration",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report


YEAR_RE = re.compile("20[0-9][0-9]")


def plan_from(result, year_range):
  link = result.find("a")
  basename = os.path.splitext(os.path.basename(link["href"]))[0]
  report_id = clean_text(basename).replace("'", "").replace(":", "")
  report_id = re.sub("-+", "-", report_id)
  report_url = urljoin(OTHER_REPORTS_URL, link["href"])

  title = clean_text(result.text)
  published_on_year = YEAR_RE.search(result.text).group(0)
  published_on = datetime.datetime(int(published_on_year), 1, 1)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "ncua",
    'inspector_url': HOMEPAGE_URL,
    'agency': "ncua",
    'agency_name': "National Credit Union Administration",
    'type': 'other',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
