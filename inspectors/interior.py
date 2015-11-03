#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector

# https://www.doioig.gov/
archive = 1993

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:

REPORT_URL_BASE = "https://www.doioig.gov"
REPORT_SEARCH_URL = ("https://www.doioig.gov/reports?keywords=&report_number="
                     "&category=All&report_type=All&date_type=report"
                     "&report_date_op=%3E%3D&report_date[date]=01/01/{}"
                     "&page={}")

def run(options):
  year_range = inspector.year_range(options, archive)
  min_year = min(year_range)
  page = 0
  last_page = 0

  while page <= last_page:
    doc = utils.beautifulsoup_from_url(REPORT_SEARCH_URL.format(min_year, page))
    last_page_link = doc.find("a", title="Go to last page")
    if last_page_link:
      href = last_page_link["href"]
      page_match = re.search("[?&]page=([0-9]+)(?:&|$)", href)
      if page_match:
        last_page = int(page_match.group(1))

    results = doc.select(".view-reports-advanced-search .views-row")
    if not results:
      raise inspector.NoReportsFoundError("Department of the Interior")
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)
    page += 1
  if last_page == 0:
    raise Exception("Did not find last page link")

def report_type_from_text(report_type_text):
  if report_type_text in ['Audit', 'External Audit']:
    return 'audit'
  elif report_type_text == 'Investigation':
    return 'investigation'
  elif report_type_text in ['Inspection', 'Verification Review', 'Memorandum', 'Management Advisory', 'Advisory']:
    return 'inspection'
  elif report_type_text in ['Assessment', 'Evaluation']:
    return 'evaluation'
  elif report_type_text == 'Semiannual Report':
    return 'semiannual_report'
  else:
    return 'other'


def report_from(result, year_range):
  title = result.header.text.strip()

  if (title == "Final Advisory Report on Costs Claimed by the State of Nevada, "
      "Department of Conservation and Natural Resources, Division of Wildlife, "
      "Under Federal Aid Grants from the U.S. Fish and Wildlife Service from "
      "July 1, 1996 through June 30, 1997"):
    return None

  landing_link = result.find("a", text="Summary")
  if landing_link:
    landing_url = urljoin(REPORT_URL_BASE, landing_link["href"])
  else:
    landing_url = None

  report_link = result.find("a", text="PDF") or result.find("a", text="Text")
  report_url = urljoin(REPORT_URL_BASE, report_link["href"])
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  summary_spans = result.select(".field-name-field-blurb .field-item")
  if summary_spans:
    summary = summary_spans[0].text.strip()
  else:
    summary = None

  published_on_text = result.select(".field-name-field-report-date .field-item")[0].text.strip()

  report_type_spans = result.select(".field-name-field-report-type .field-item")
  if report_type_spans:
    report_type_text = report_type_spans[0].text.strip()
    report_type = report_type_from_text(report_type_text)
  else:
    report_type = "other"

  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  result = {
    'inspector': 'interior',
    'inspector_url': 'https://www.doioig.gov/',
    'agency': 'interior',
    'agency_name': 'Department of the Interior',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if landing_url:
    result['landing_url'] = landing_url
  if summary:
    result['summary'] = summary
  return result


utils.run(run) if (__name__ == "__main__") else None
