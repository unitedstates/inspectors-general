#!/usr/bin/env python

import datetime
import logging
import os
from bs4 import BeautifulSoup
from utils import utils, inspector

archive = 2007

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.prc.gov/oig-reports?page="

def run(options):
  year_range = inspector.year_range(options, archive)

  # Find the number of pages to iterate
  doc = BeautifulSoup(utils.download(REPORTS_URL), "lxml")
  page_count = int(doc.select("li.pager-last a")[0]['href'][-1:])

  # Iterate over those pages
  for page in range(0, page_count + 1):
    response = utils.download(REPORTS_URL + str(page))
    doc = BeautifulSoup(response, "lxml")
    results = doc.select(".reports")
    if not results:
      if page == 0:
        raise inspector.NoReportsFoundError("Postal Regulatory Commission")
      else:
        break
    for index, result in enumerate(results):
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def type_from_title(title):
  if 'Semiannual Report' in title:
    return 'semiannual_report'
  elif 'Audit' in title:
    return 'audit'
  elif 'Inspection' in title:
    return 'inspection'
  else:
    return 'other'

def report_from(result, year_range):
  published_on_text = result.select("td")[0].text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  title = result.select(".views-field-title")[0].text.strip()

  report_type = type_from_title(title)

  report_url = result.select(".rolldownload a")[0]['href']
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "prc",
    'inspector_url': "http://www.prc.gov/offices/oig",
    'agency': "prc",
    'agency_name': "Postal Regulatory Commission",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

utils.run(run) if (__name__ == "__main__") else None
