#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.eeoc.gov/eeoc/oig/index.cfm
archive = 2003

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "http://www.eeoc.gov/eeoc/oig/"

REPORT_PUBLISHED_MAP = {
  '2005-02-amr': datetime.datetime(2005, 1, 1),
  '2005-03-prop': datetime.datetime(2005, 9, 1),
  '2005-08-mgt': datetime.datetime(2005, 10, 27),
  'nccrep': datetime.datetime(2006, 6, 29),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  doc = BeautifulSoup(utils.download(REPORTS_URL))
  semiannual_report_results, other_results = doc.select("table tr")[1].select("td")
  merge_items(semiannual_report_results)
  merge_items(other_results)

  for result in semiannual_report_results.select("li"):
    report = semiannual_report_from(result, year_range, title_prefix="Semiannual Report - ")
    if report:
      inspector.save_report(report)

  for result in other_results.select("li"):
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def semiannual_report_from(result, year_range, title_prefix=None):
  link = result.find("a")
  report_url = urljoin(REPORTS_URL, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  published_on_text = link.text.split("-")[-1].strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  title = link.text
  if title_prefix:
    title = "{}{}".format(title_prefix, title)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "eeoc",
    'inspector_url': "http://www.eeoc.gov/eeoc/oig/",
    'agency': "eeoc",
    'agency_name': "Equal Employment Opportunity Commission",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

def report_from(result, year_range):
  link = result.find("a")
  report_url = urljoin(REPORTS_URL, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    try:
      published_on_text = "-".join(re.search('\((\w+) (\d+),?\s(\d{4})\)', result.text).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')
    except AttributeError:
      try:
        published_on_text = "-".join(re.search('\((\w+)\s(\d{4})\)', result.text).groups())
        published_on = datetime.datetime.strptime(published_on_text, '%B-%Y')
      except AttributeError:
        published_on_text = "-".join(re.search('(\w+) (\d+),?\s(\d{4})', result.text).groups())
        published_on = datetime.datetime.strptime(published_on_text, '%B-%d-%Y')

  title = link.text

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': "eeoc",
    'inspector_url': "http://www.eeoc.gov/eeoc/oig/",
    'agency': "eeoc",
    'agency_name': "Equal Employment Opportunity Commission",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def merge_items(parent):
  '''This function loops through all the <li> tags in a subtree of a document,
  checks if two neighboring items each contain one link to the same href,
  and if they do, merges them together into one <li> with one <a> tag.'''

  items = parent.find_all("li")
  for i in range(len(items) - 2, -1, -1):
    first_item = items[i]
    second_item = items[i+1]

    first_links = first_item.find_all("a")
    if len(first_links) != 1:
      continue
    second_links = second_item.find_all("a")
    if len(second_links) != 1:
      continue
    first_link = first_links[0]
    second_link = second_links[0]

    if first_link.get("href") != second_link.get("href"):
      continue

    # Transplant the contents of the second link into the end of the first link
    first_link.append(" ")
    while second_link.contents:
      temp = second_link.contents[0].extract()
      first_link.append(temp)

    # Discard the now-empty second link
    second_link.extract()

    # Transplant everything else inside the <li> to the end of the first <li>
    while second_item.contents:
      temp = second_item.contents[0].extract()
      first_item.append(temp)

    # Discard the now-empty list item
    second_item.extract()

utils.run(run) if (__name__ == "__main__") else None
