#!/usr/bin/env python

import datetime
import logging
import os
import re

from utils import utils, inspector, admin

# https://www.sigtarp.gov
archive = 2009

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDITS_URL = "https://www.sigtarp.gov/pages/audit.aspx"
TESTIMONY_URL = "https://www.sigtarp.gov/pages/testimony.aspx"
QUARTERLY_REPORTS_URL = "https://www.sigtarp.gov/pages/Reports-Testimony-Home.aspx"

REPORT_URLS = [
  ("audit", AUDITS_URL),
  ("testimony", TESTIMONY_URL),
]

LINK_RE = re.compile("^([A-Za-z ]+) \\(([A-Z][a-z]+ [0-9]+, [0-9]+)\\)$")

QUARTERLY_REPORT_DATES = {
  "SIGTARP_Initial_Report_to_the_Congress": datetime.datetime(2009, 2, 6),
  "April2009_Quarterly_Report_to_Congress": datetime.datetime(2009, 4, 21),
  "July2009_Quarterly_Report_to_Congress": datetime.datetime(2009, 7, 21),
  "October2009_Quarterly_Report_to_Congress": datetime.datetime(2009, 10, 21),
  "January2010_Quarterly_Report_to_Congress": datetime.datetime(2010, 1, 30),
  "April2010_Quarterly_Report_to_Congress": datetime.datetime(2010, 4, 20),
  "July2010_Quarterly_Report_to_Congress": datetime.datetime(2010, 7, 21),
  "October2010_Quarterly_Report_to_Congress": datetime.datetime(2010, 10, 26),
  "January2011_Quarterly_Report_to_Congress": datetime.datetime(2011, 1, 26),
  "April2011_Quarterly_Report_to_Congress": datetime.datetime(2011, 4, 28),
  "July2011_Quarterly_Report_to_Congress": datetime.datetime(2011, 7, 28),
  "October2011_Quarterly_Report_to_Congress": datetime.datetime(2011, 10, 27),
}


def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, report_url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(report_url)
    results = doc.select("td.mainInner div.ms-WPBody > div > ul > li")

    if not results:
      raise inspector.NoReportsFoundError("SIGTARP ({})".format(report_type))

    for result in results:
      report = report_from(result, report_type, year_range)
      if report:
        inspector.save_report(report)

  doc = utils.beautifulsoup_from_url(QUARTERLY_REPORTS_URL)
  results = doc.select("#MSOZoneCell_WebPartWPQ3 .s4-wpTopTable a")

  if not results:
    raise inspector.NoReportsFoundError("SIGTARP (quarterly reports)")

  for result in results:
    report = quarterly_report_from(result, year_range)
    if report:
      inspector.save_report(report)


def report_from(result, report_type, year_range):
  result_link = result.find("a")
  title = result_link.text

  report_url = result_link.get('href')
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on_text = result.select("div.custom_date")[0].text.lstrip("-")
  if published_on_text == "":
    match = LINK_RE.match(result_link.text.strip())
    published_on_text = match.group(2)
    title = result.find("div", class_="groupheader").text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'sigtarp',
    'inspector_url': "https://www.sigtarp.gov",
    'agency': 'sigtarp',
    'agency_name': "Special Inspector General for the Troubled Asset Relief Program",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report


def quarterly_report_from(result, year_range):
  report_url = result['href']
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  groupheader = result.parent.parent.parent.parent.find("div", class_="groupheader")
  year = int(groupheader.text.strip())
  if year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Quarterly Report to Congress, {}, {}".format(year, result.text.strip())

  if report_id in QUARTERLY_REPORT_DATES:
    published_on = QUARTERLY_REPORT_DATES[report_id]
  else:
    published_on = None

  if published_on is None:
    try:
      published_on = datetime.datetime.strptime(report_id, "%B_%d_%Y_Report_to_Congress")
    except ValueError:
      pass

  if published_on is None:
    try:
      published_on = datetime.datetime.strptime(report_id, "%B_%d_%Y_Report_To_Congress")
    except ValueError:
      pass

  if published_on is None:
    try:
      published_on = datetime.datetime.strptime(report_id, "%B_%d_%Y_Quarterly_Report_to_Congress")
    except ValueError:
      pass

  if published_on is None:
    admin.log_no_date("sigtarp", report_id, title, report_url)
    return

  report = {
    'inspector': 'sigtarp',
    'inspector_url': "https://www.sigtarp.gov",
    'agency': 'sigtarp',
    'agency_name': "Special Inspector General for the Troubled Asset Relief Program",
    'type': 'quarterly',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
