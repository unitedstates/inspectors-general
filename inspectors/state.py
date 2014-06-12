#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
import re

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.state.gov/lbry/index.htm
# Oldest report: 1992?

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated, which
#            correspond to the topics defined on the site. For example:
#            'A,I,BBG'
#            Defaults to all topics.
#
#            A    - Audits
#            I    - Inspections
#            BBG  - Broadcasting Board of Governors
#            IT   - Information Technology
#            MA   - Management Alerts and Other Action Items
#            SAR  - Semiannual Reports to Congress
#            OC   - Other Reports to Congress
#            RA   - Recovery Act
#            RAF  - Recovery Act Financial Reports
#            CT   - Congressional Testimony
#            SPWP - Strategic, Performance, and Work Plans
#            O    - Other OIG Reports and Publications
#            PR   - Peer Reviews
#            P    - Publications

# Notes for IG's web team:
#  - Don't have two links for the same report (ex http://oig.state.gov/aboutoig/offices/cpa/tstmny/2009/index.htm)
#  - Fix link to 'Broadcasting Board of Governors' on http://oig.state.gov/lbry/archives/isp/index.htm

TOPIC_TO_URL = {
  "A": "http://oig.state.gov/lbry/audrpts/index.htm",
  "I": "http://oig.state.gov/lbry/isprpts/index.htm",
  "BBG": "http://oig.state.gov/lbry/bbgreports/index.htm",
  "IT": "http://oig.state.gov/lbry/im/index.htm",
  "MA": "http://oig.state.gov/lbry/alerts/index.htm",
  "SAR": "http://oig.state.gov/lbry/sar/index.htm",
  "OC": "http://oig.state.gov/lbry/congress/index.htm",
  "RA": "http://oig.state.gov/arra/plansreports/index.htm",
  "RAF": "http://oig.state.gov/arra/financialactivity/index.htm",
  "CT": "http://oig.state.gov/aboutoig/offices/cpa/tstmny/index.htm",
  "SPWP": "http://oig.state.gov/lbry/plans/index.htm",
  "O": "http://oig.state.gov/lbry/other/c26047.htm",
  "FOIA": "http://oig.state.gov/foia/readroom/index.htm",
  "PR": "http://oig.state.gov/lbry/other/c39666.htm",
  "P": "http://oig.state.gov/lbry/other/c26046.htm",
}

ARCHIVE_TOPICS = {
  "A": "http://oig.state.gov/lbry/archives/aud/index.htm",
  "I": "http://oig.state.gov/lbry/archives/isp/index.htm",
  "BBG": "http://oig.state.gov/lbry/archives/bbg/index.htm",
  "IT": "http://oig.state.gov/lbry/archives/it/index.htm",
  "SAR": "http://oig.state.gov/lbry/archives/sar/index.htm",
}

TOPIC_NAMES = {
  "A": "Audits",
  "I": "Inspections",
  "BBG": "Broadcasting Board of Governors",
  "IT": "Information Technology",
  "MA": "Management Alerts and Other Action Items",
  "SAR": "Semiannual Reports to Congress",
  "OC": "Other Reports to Congress",
  "RA": "Recovery Act",
  "RAF": "Recovery Act Financial Reports",
  "CT": "Congressional Testimony",
  "SPWP": "Strategic, Performance, and Work Plans",
  "O": "Other OIG Reports and Publications",
  "FOIA": "Freedom of Information Act",
  "PR": "Peer Reviews",
  "P": "Publications",
}

NESTED_TOPICS = ["A", "I", "BBG", "CT"]

# These are links that appear like reports, but are not.
BLACKLIST_REPORT_URLS = [
  # 404, should probably investigate
  "http://oig.state.gov/documents/organization/106950.pdf",

  # 404s, probably don't need to investigate (should just be a bio links)
  "http://oig.state.gov/about/c25120.htm",
  "http://oig.state.gov/audits/c7795.htm",

  # TODO we probably want these
  "http://oig.state.gov/documents/organization/207582.pdf",  # From http://oig.state.gov/aboutoig/offices/cpa/tstmny/2013/index.htm
  "http://oig.state.gov/lbry/archives/it/17998.htm",  # From http://oig.state.gov/lbry/archives/it/index.htm
]

# Sometimes a report will be linked to multiple times on the same page. We only
# want to capture the first time it is linked.
# See the links to http://oig.state.gov/documents/organization/107793.pdf
# on http://oig.state.gov/aboutoig/offices/cpa/tstmny/2008/index.htm
# for an example
REPORT_URLS_SEEN = set()

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    topic_url = TOPIC_TO_URL[topic]
    extract_reports_for_topic(topic, topic_url, year_range)

    if topic in ARCHIVE_TOPICS:
      archive_url = ARCHIVE_TOPICS[topic]
      extract_reports_for_topic(topic, archive_url, year_range)

def extract_reports_for_topic(topic, topic_url, year_range):
  if topic in NESTED_TOPICS:
    subtopic_link_map = get_page_highlights(topic_url)
  else:
    subtopic_link_map = {None: topic_url}

  topic_name = TOPIC_NAMES[topic]
  for subtopic_name, subtopic_url in subtopic_link_map.items():
    logging.debug("## Processing subtopic %s" % subtopic_name)
    extract_reports_for_subtopic(subtopic_url, year_range, topic_name, subtopic_name)

def extract_reports_for_subtopic(subtopic_url, year_range, topic, subtopic=None):
  if subtopic_url.startswith("http://httphttp://"):
    # See notes to IG's web team
    subtopic_url = subtopic_url.replace("http://http", "")

  body = utils.download(subtopic_url)
  doc = BeautifulSoup(body)
  results = doc.select("#body-row02-col02andcol03 a")

  if not results:
    results = doc.select("#body-row02-col01andcol02andcol03 a")
  if not results and "There are currently no reports in this category" not in doc.text:
    raise AssertionError("No report links found for %s" % subtopic_url)

  for result in results:
    report = report_from(result, year_range, topic, subtopic)
    if report:
      inspector.save_report(report)

def report_from(result, year_range, topic, subtopic=None):
  title = result.text.strip()
  report_url = result['href']

  # There are lots of links and formats. Ignore those that are not to this site.
  if "oig.state.gov" not in report_url:
    return

  # These are inline links to officials in the OIG
  if "http://oig.state.gov/aboutoig/bios" in report_url:
    return

  if report_url in BLACKLIST_REPORT_URLS:
    return

  # See the definition of REPORT_URLS_SEEN for more
  if report_url in REPORT_URLS_SEEN:
    return

  REPORT_URLS_SEEN.add(report_url)

  if ("archives" in title.lower()
      or 'foia' in title.lower()
      or 'foia' in report_url
      or report_url in [
        'http://oig.state.gov/lbry/sar/index.htm',
        'http://oig.state.gov/lbry/congress/index.htm'
        ]
    ):
    return None

  # TODO this is way to hacky. See http://oig.state.gov/aboutoig/offices/cpa/tstmny/2009/index.htm
  if 'Acting Inspector General' in title:
    return

  # These are always just dupes of the previous report
  if title == 'Click here for Oral Remarks related to this Testimony.':
    return

  logging.debug("## Processing report %s" % report_url)

  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]

  try:
    previous_sibling_text = str(result.previous_sibling).strip()
  except AttributeError:
    previous_sibling_text = ""

  try:
    published_on = datetime.datetime.strptime(previous_sibling_text, "-%m/%d/%y")
  except ValueError:
    try:
      published_on = datetime.datetime.strptime("-".join(title.split()[-2:]), "%b-%Y")
    except ValueError:
      # Fall back to when the report was posted to the site
      posted_text = result.find_parent("p").previous_sibling.previous_sibling.text
      published_on = datetime.datetime.strptime(posted_text, 'Posted %B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  result = {
    'inspector': 'state',
    'inspector_url': 'http://oig.state.gov/',
    'agency': 'state',
    'agency_name': 'Department of State',
    'report_id': report_id,
    'topic': topic,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if subtopic:
    result['subtopic'] = subtopic
  return result

def get_page_highlights(page_url):
  body = utils.download(page_url)
  doc = BeautifulSoup(body)

  page_id = re.search("item_id = '(\d+)';", doc.find(language='javascript').text).groups()[0]

  # The first hightlights page just gives a link to the real page
  page_highlights_url = "http://oig.state.gov/highlights_xml/c_%s.xml" % page_id
  page_highlights_body = utils.download(page_highlights_url)
  page_highlights = BeautifulSoup(page_highlights_body)
  real_highlights_url = page_highlights.find("highlightpath")

  if not real_highlights_url:
    page_highlights_url = "http://oig.state.gov/learnmore_xml/c_%s.xml" % page_id
    page_highlights_body = utils.download(page_highlights_url)
    page_highlights = BeautifulSoup(page_highlights_body)
    real_highlights_url = page_highlights.find("highlightpath")

  page_highlights_url = "http://oig.state.gov%s" % real_highlights_url.text
  page_highlights_body = utils.download(page_highlights_url)
  page_highlights = BeautifulSoup(page_highlights_body)
  return {
    link.text.replace(u'•', '').strip(): link['href']
    for link
    in page_highlights.select("a")
  }

utils.run(run) if (__name__ == "__main__") else None
