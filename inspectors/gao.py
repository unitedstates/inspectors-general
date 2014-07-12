#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.gao.gov/about/workforce/ig_reports.html
# Oldest report: 2008

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.gao.gov/about/workforce/ig_reports.html"
SEMIANNUAL_REPORTS_URL = "http://www.gao.gov/about/workforce/ig_semiannual.html"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit and semiannual reports
  for reports_url in [REPORTS_URL, SEMIANNUAL_REPORTS_URL]:
    doc = beautifulsoup_from_url(reports_url)
    results = doc.select("div.listing")
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, year_range):
  link = result.select("a")[0]
  title = link.text
  landing_url = urljoin(REPORTS_URL, link.get('href'))
  report_id_node, published_node = result.select("div.release_info")
  report_id = report_id_node.text.strip().replace(",", "")
  published_on = datetime.datetime.strptime(published_node.text, '%b %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("Scraping landing url: %s", landing_url)
  landing_page = beautifulsoup_from_url(landing_url)
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
    'url': report_url,
    'text_url': text_report_url,
    'landing_url': landing_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None