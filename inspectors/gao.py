#!/usr/bin/env python

import datetime
import logging
from urllib.parse import urljoin

from utils import utils, inspector

# http://www.gao.gov/about/workforce/ig_reports.html
archive = 2008

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#
# * where's the reports before 2008?

REPORTS_URL = "http://www.gao.gov/about/workforce/ig_reports.html"
SEMIANNUAL_REPORTS_URL = "http://www.gao.gov/about/workforce/ig_semiannual.html"

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit and semiannual reports
  for reports_url in [REPORTS_URL, SEMIANNUAL_REPORTS_URL]:
    doc = utils.beautifulsoup_from_url(reports_url)
    results = doc.select("div.listing")
    if not results:
      raise inspector.NoReportsFoundError("GAO (%s)" % reports_url)
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, year_range):
  link = result.select("a")[0]
  title = link.text
  landing_url = urljoin(REPORTS_URL, link.get('href'))
  report_url_node, publication_info_node = result.select("div.release_info")
  publication_info = publication_info_node.text.split(":")
  report_id = publication_info[0].strip().replace(",", "")
  published_on = datetime.datetime.strptime(publication_info[1].strip(), '%b %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("Scraping landing url: %s", landing_url)
  landing_page = utils.beautifulsoup_from_url(landing_url)
  summary = landing_page.select("div.left_col")[0].text.strip()

  pdf_link = landing_page.select("#link_bar > a")[0]
  report_url = urljoin(REPORTS_URL, pdf_link.get('href'))

  text_link = landing_page.select("#add_material a")[-1]
  text_report_url = urljoin(REPORTS_URL, text_link.get('href'))

  report = {
    'inspector': 'gao',
    'inspector_url': 'http://www.gao.gov/about/workforce/ig.html',
    'agency': 'gao',
    'agency_name': 'Government Accountability Office',
    'report_id': report_id,
    'summary': summary,
    'url': report_url,
    'text_url': text_report_url,
    'landing_url': landing_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report


utils.run(run) if (__name__ == "__main__") else None
