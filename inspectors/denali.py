#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import Tag
from utils import utils, inspector

# http://www.oig.denali.gov/
archive = 2006

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#   - many reports could use some OCRing, or re-upload in their original form.

REPORTS_URL = "http://oig.denali.gov"

REPORT_PUBLISHED_MAPPING = {
  "DCOIG-16-001-A": datetime.datetime(2015, 11, 13),
  "FY-14-Denali-Commission-Financial-Performance-Report": datetime.datetime(2014, 11, 26),
  "FY-12-Denali-Commission-Financial-Report": datetime.datetime(2012, 11, 15),
  "FY-11-Denali-Commission-Financial-Report": datetime.datetime(2011, 11, 22),
  "FY-10-Denali-Commission-Financial-Performance-Report": datetime.datetime(2010, 11, 22),
}

DATE_RE = re.compile("(20[0-9][0-9]\\.[01][0-9])(?: *- *(.*))?")

def run(options):
  year_range = inspector.year_range(options, archive)

  doc = utils.beautifulsoup_from_url(REPORTS_URL)

  results = None
  for section in doc.find_all("section"):
    if section.h4 and section.h4.text.strip() == "Publications":
      results = section.find_all("a")
      break

  if not results:
    raise inspector.NoReportsFoundError("Denali Commission")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  # walk backwards through the doc to find the header title
  for element in result.previous_elements:
    if element and \
        isinstance(element, Tag) and \
        element.name == "span" and \
        element.has_attr("class") and \
        "collapseomatic" in element["class"]:
      header = element.text.strip().lower()
      break
  else:
    raise Exception("Couldn't find the header for %s" % result)

  if header.startswith("inspection"):
    category = "inspection"
  elif header.startswith("semiannual"):
    category = "semiannual_report"
  else:
    category = "other"

  report_id = os.path.splitext(os.path.basename(result['href']))[0]
  report_url = urljoin(REPORTS_URL, result['href'])
  title = inspector.sanitize(result.text)

  # Each financial/performance report is linked twice, once for the IG's
  # transmittal letter and independent auditor's report, and once for
  # the IG's "Perspective on Management and Performance Challenges."
  # Skip the first one and save the second
  if "IG's Transmittal Letter and Independent Auditor's Report" in title \
      and "(pages" in title:
    return None
  elif title == "Hotline Poster":
    return None

  published_on = REPORT_PUBLISHED_MAPPING.get(title)
  if not published_on:
    published_on = REPORT_PUBLISHED_MAPPING.get(report_id)

  if not published_on:
    date_match = DATE_RE.match(title)
    if date_match:
      published_on = datetime.datetime.strptime(date_match.group(1), "%Y.%m")
      if date_match.lastindex == 2:
        title = date_match.group(2)
      elif header.startswith("semiannual"):
        title = published_on.strftime("Semiannual Report to Congress, %B %Y")
      else:
        raise Exception("No good title for %s" % report_id)

  if not published_on:
    inspector.log_no_date(report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "denali",
    'inspector_url': "http://www.oig.denali.gov",
    'agency': "denali",
    'agency_name': "Denali Commission",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': category,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
