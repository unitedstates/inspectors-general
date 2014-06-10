#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.state.gov/lbry/index.htm
# Oldest report: 2000?

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated, which
#            correspond to the topics defined on the site. For example:
#            'A,I'
#            Defaults to all topics.
#
#            A    - Audits
#            I    - Inspections
#            BBG  - Broadcasting Board of Governors
#            IT   - Information Technology
#            MA   - Management Alerts and Other Action Items
#            SR   - Semiannual Reports to Congress
#            OC   - Other Reports to Congress
#            RA   - Recovery Act
#            CT   - Congressional Testimony
#            SPWP - Strategic, Performance, and Work Plans
#            O    - Other OIG Reports and Publications
#            FOIA - FOIA Electronic Reading Room


# Notes for IG's web team:

TOPIC_TO_URL = {
  "A": "http://oig.state.gov/lbry/audrpts/index.htm",
  "I": "http://oig.state.gov/lbry/isprpts/index.htm",
  "BBG": "http://oig.state.gov/lbry/bbgreports/index.htm",
  "IT": "http://oig.state.gov/lbry/im/index.htm",
  "MA": "http://oig.state.gov/lbry/alerts/index.htm",
  "SR": "http://oig.state.gov/lbry/sar/index.htm",
  "OC": "http://oig.state.gov/lbry/congress/index.htm",
  "RA": "http://oig.state.gov/arra/index.htm",
  # "CT": "http://oig.state.gov/aboutoig/offices/cpa/tstmny/index.htm",
  # TODO the highlights are years...
  "SPWP": "http://oig.state.gov/lbry/plans/index.htm",
  "O": "http://oig.state.gov/lbry/other/index.htm",
  # "FOIA": "http://oig.state.gov/foia/readroom/index.htm",
  # TODO implement
}

NESTED_TOPICS = ["A", "I", "BBG"]

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    topic_url = TOPIC_TO_URL[topic]

    if topic in NESTED_TOPICS:
      subtopic_link_map = get_page_highlights(topic_url)
    else:
      # TODO
      subtopic_link_map = {None: topic_url}

    for subtopic_name, subtopic_link in subtopic_link_map.items():
      print(topic, subtopic_name, subtopic_link)

    # # Suggested parser, Beautiful Soup 4.
    # doc = BeautifulSoup(body)
    # results = doc.select("some-selector")

    # for result in results:
    #   report = report_from(result)
    #   inspector.save_report(report)


# suggested: construct URL based on options
def url_for(options, page = 1):
  pass

# suggested: a function that gets report details from a parent element,
# extract a dict of details that are ready for inspector.save_report().
def report_from(result):
  pass


def get_page_highlights(page_url):
  body = utils.download(page_url)
  doc = BeautifulSoup(body)

  page_id = re.search("item_id = '(\d+)';", doc.find(language='javascript').text).groups()[0]

  # The first hightlights page just gives a link to the real page
  page_highlights_url = "http://oig.state.gov/highlights_xml/c_%s.xml" % page_id
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
