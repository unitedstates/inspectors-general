#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from urllib.parse import urljoin, urlencode
import re
import os
import logging
from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.oig.dot.gov/
# oldest year: 1996

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated.
#            e.g. "A,IN". Defaults to all topics.
#
#          A    - Audits
#          IN   - Investigations
#          T    - Testimony
#          C    - Correspondence
#          R    - Recovery Act
#          SA   - Semiannual Reports


TOPIC_TO_URL = {
  "A": "http://www.oig.dot.gov/audits",
  "IN": "http://www.oig.dot.gov/investigations",
  "T": "http://www.oig.dot.gov/testimony",
  "C": "http://www.oig.dot.gov/correspondence",
  "R": "http://www.oig.dot.gov/recovery",
  "SA": "http://www.oig.dot.gov/semiannual-reports",
}

BASE_REPORT_PAGE_URL = BASE_REPORT_URL = "http://www.oig.dot.gov/"

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    year_urls = urls_for(year_range, topic)
    for year_url in year_urls:
      body = utils.download(year_url)

      doc = BeautifulSoup(body)
      results = doc.select(".item-list ul li")

      for result in results:
        report = report_from(result, year_range)
        if report:
          inspector.save_report(report)

def urls_for(year_range, topic):
  topic_url = TOPIC_TO_URL[topic]
  return ["%s?date_filter[value][year]=%s" % (topic_url, year) for year in year_range]

def report_from(result, year_range):
  published_date_text = result.select('.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%m.%d.%Y")

  landing_url_link = result.select('a')[0]
  landing_url_relative = landing_url_link['href']
  title = landing_url_link.text
  landing_url = urljoin(BASE_REPORT_PAGE_URL, landing_url_relative)

  if published_on.year not in year_range:
    # Some reports come in from the 'Most Popular' section of the page and that
    # section does not obey the year filters
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("### Processing report %s" % landing_url)

  report_page_body = utils.download(landing_url)
  report_page = BeautifulSoup(report_page_body)
  summary = report_page.select(".summary-body")[0].text.strip()

  unreleased = False
  missing = False
  try:
    report_url = urljoin(BASE_REPORT_URL, report_page.select(".download-pdf a")[0]['href'])
  except IndexError as exc:
    if 'For Official Use Only' in summary:
      unreleased = True
      report_url = None
      report_id = landing_url.split("/")[-1]
    else:
      raise exc
  else:
    report_id = os.path.splitext(os.path.basename(report_url))[0]

  report = {
    'inspector': 'dot',
    'inspector_url': 'https://www.oig.dot.gov/',
    'agency': 'dot',
    'agency_name': 'Development of Transportation',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'landing_url': landing_url,
    'summary': summary,
  }
  if unreleased:
    report['unreleased'] = unreleased
  if missing:
    report['missing'] = missing
  return report

utils.run(run) if (__name__ == "__main__") else None
