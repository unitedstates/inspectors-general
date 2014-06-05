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

BLACKLIST_REPORT_URLS = [
  "http://www.oig.dot.gov/library-item/5299",
  "http://www.oig.dot.gov/library-item/5366",
  "http://www.oig.dot.gov/library-item/5367",
  "http://www.oig.dot.gov/library-item/5375",
  "http://www.oig.dot.gov/library-item/5395",
  "http://www.oig.dot.gov/library-item/5644",
  "http://www.oig.dot.gov/library-item/6022",
  "http://www.oig.dot.gov/library-item/6279",
  "http://www.oig.dot.gov/library-item/6286",
  "http://www.oig.dot.gov/library-item/6287",
  "http://www.oig.dot.gov/library-item/6288",
  "http://www.oig.dot.gov/library-item/6289",
  "http://www.oig.dot.gov/library-item/6293",
  "http://www.oig.dot.gov/library-item/6294",
  "http://www.oig.dot.gov/library-item/6295",
  "http://www.oig.dot.gov/library-item/6296",
  "http://www.oig.dot.gov/library-item/6297",
  "http://www.oig.dot.gov/library-item/6304",
  "http://www.oig.dot.gov/library-item/6305",
  "http://www.oig.dot.gov/library-item/6306",
  "http://www.oig.dot.gov/library-item/6307",
  "http://www.oig.dot.gov/library-item/6308",
  "http://www.oig.dot.gov/library-item/6309",
  "http://www.oig.dot.gov/library-item/6310",
  "http://www.oig.dot.gov/library-item/6310",
  "http://www.oig.dot.gov/library-item/6311",
  "http://www.oig.dot.gov/library-item/6317",
  "http://www.oig.dot.gov/library-item/6318",
  "http://www.oig.dot.gov/library-item/6319",
  "http://www.oig.dot.gov/library-item/6320",
  "http://www.oig.dot.gov/library-item/6328",
  "http://www.oig.dot.gov/library-item/6329",
  "http://www.oig.dot.gov/library-item/6330",
  "http://www.oig.dot.gov/library-item/6331",
  "http://www.oig.dot.gov/library-item/6400",
  "http://www.oig.dot.gov/library-item/6401",
  "http://www.oig.dot.gov/library-item/6402",
  "http://www.oig.dot.gov/library-item/6411",
  "http://www.oig.dot.gov/library-item/6411",
  "http://www.oig.dot.gov/library-item/6412",
  "http://www.oig.dot.gov/library-item/6413",
  "http://www.oig.dot.gov/library-item/6420",
  "http://www.oig.dot.gov/library-item/6425",
  "http://www.oig.dot.gov/library-item/6426",
  "http://www.oig.dot.gov/library-item/6426",
  "http://www.oig.dot.gov/library-item/6428",
  "http://www.oig.dot.gov/library-item/6429",
  "http://www.oig.dot.gov/library-item/6430",
  "http://www.oig.dot.gov/library-item/6440",
  "http://www.oig.dot.gov/library-item/6441",
  "http://www.oig.dot.gov/library-item/6442",
  "http://www.oig.dot.gov/library-item/6443",
  "http://www.oig.dot.gov/library-item/6444",
  "http://www.oig.dot.gov/library-item/6446",
  "http://www.oig.dot.gov/library-item/6448",
  "http://www.oig.dot.gov/library-item/6449",
  "http://www.oig.dot.gov/library-item/6463",
  "http://www.oig.dot.gov/library-item/6464",
  "http://www.oig.dot.gov/library-item/6465",
  "http://www.oig.dot.gov/library-item/6467",
  "http://www.oig.dot.gov/library-item/6468",
  "http://www.oig.dot.gov/library-item/6491",
  "http://www.oig.dot.gov/library-item/6493",
  "http://www.oig.dot.gov/library-item/6504",
  "http://www.oig.dot.gov/library-item/6505",
  "http://www.oig.dot.gov/library-item/6505",
  "http://www.oig.dot.gov/library-item/6515",
  "http://www.oig.dot.gov/library-item/6516",
  "http://www.oig.dot.gov/library-item/6518",
  "http://www.oig.dot.gov/library-item/6519",
  "http://www.oig.dot.gov/library-item/6520",
  "http://www.oig.dot.gov/library-item/6521",
  "http://www.oig.dot.gov/library-item/6526",
  "http://www.oig.dot.gov/library-item/6527",
  "http://www.oig.dot.gov/library-item/6530",
  "http://www.oig.dot.gov/library-item/6531",
  "http://www.oig.dot.gov/library-item/6532",
  "http://www.oig.dot.gov/library-item/6550",
  "http://www.oig.dot.gov/library-item/6551",
  "http://www.oig.dot.gov/library-item/6552",
]

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

      # Suggested parser, Beautiful Soup 4.
      doc = BeautifulSoup(body)
      results = doc.select(".item-list ul li")

      for result in results:
        report = report_from(result)
        if report:
          inspector.save_report(report)

def urls_for(year_range, topic):
  topic_url = TOPIC_TO_URL[topic]
  return ["%s?date_filter[value][year]=%s" % (topic_url, year) for year in year_range]

def report_from(result):
  published_date_text = result.select('.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%m.%d.%Y")

  landing_url_link = result.select('a')[0]
  landing_url_relative = landing_url_link['href']
  title = landing_url_link.text
  landing_url = urljoin(BASE_REPORT_PAGE_URL, landing_url_relative)
  logging.debug("### Processing report %s" % landing_url)

  report_page_body = utils.download(landing_url)
  report_page = BeautifulSoup(report_page_body)

  unreleased = False
  if landing_url in BLACKLIST_REPORT_URLS:
    unreleased = True
    report_url = None
    report_id = landing_url.split("/")[-1]
  else:
    report_url = urljoin(BASE_REPORT_URL, report_page.select(".download-pdf a")[0]['href'])
    report_id = os.path.splitext(os.path.basename(report_url))[0]

  summary = report_page.select(".summary-body")[0].text.strip()

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
  return report

utils.run(run) if (__name__ == "__main__") else None
