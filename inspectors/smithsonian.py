#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.si.edu/OIG
# Oldest report: 2003

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

# The general strategy for this report is a bit complicated. First we go through
# the RSS feed and add reports. This gives us a bunch of reports with definitive
# published dates. Unfortunately, this feed is only updated sporadically.
# Next, we use the main audits page since this also gives us accurate published
# dates for the newer reports that are listed. Lastly, we fall back to the
# archives page, which unfortunately only lists the year the report was
# published.
#
# Since a report can be listed on multiple pages, it is important to use
# consistent report ids across pages.

RSS_URL = "http://www.si.edu/Content/OIG/Misc/OIG-RSS.xml"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the RSS feed
  doc = BeautifulSoup(utils.download(RSS_URL))
  results = doc.select("item")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, year_range):
  report_url = result.find("link").next_sibling.strip()
  if report_url.rstrip("/") == 'http://www.si.edu/oig':
    # This is the default url the IG uses for announcements of things like
    # a website redesign or changes to the RSS feed.
    return

  file_type = None
  if not report_url.endswith(".pdf"):
    file_type = "html"

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  title = result.find("title").text
  published_on_text = result.find("pubdate").text
  published_on = datetime.datetime.strptime(published_on_text, '%a, %d %b %Y %H:%M:%S %z').date()

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'smithsonian',
    'inspector_url': 'http://www.si.edu/OIG',
    'agency': 'smithsonian',
    'agency_name': 'Smithsonian Institution',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if file_type:
    report['file_type'] = file_type
  return report

utils.run(run) if (__name__ == "__main__") else None
