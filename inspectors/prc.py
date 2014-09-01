#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.prc.gov/prc-pages/about/offices/office.aspx?office=oig
archive = 2007

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.prc.gov/prc-pages/about/offices/reportOIG.aspx"

# This is necessary for the page to return proper responses
COOKIES = {
  "ASP.NET_SessionId": "",
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Find the number of pages to iterate
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  page_count_text = doc.select("div.AspNet-GridView-Pagination")[0].text
  page_count = int(re.search('Page 1 of (\d+)', page_count_text).groups()[0])

  # Iterate over those pages
  for page in range(1, page_count + 1):
    response = utils.scraper.post(REPORTS_URL,
      data={
          "__EVENTTARGET": "ctl00$ctl00$MainContent$NavTreeSubContent$sv$GridViewSummary",
          "__EVENTARGUMENT": "Page${page_number}".format(page_number=page),
      },
      cookies=COOKIES,
    )
    doc = BeautifulSoup(response.content)
    results = doc.select("div.AspNet-GridView table tr")
    if not results:
      break
    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
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

  title = result.select("td")[1].text

  report_type = type_from_title(title)

  report_link = result.find("a")
  report_url = urljoin(REPORTS_URL, report_link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "prc",
    'inspector_url': "http://www.prc.gov/prc-pages/about/offices/office.aspx?office=oig",
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
