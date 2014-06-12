#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
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
  "RA": "http://oig.state.gov/arra/plansreports/index.htm",
  "RAF": "http://oig.state.gov/arra/financialactivity/index.htm",

  # "CT": "http://oig.state.gov/aboutoig/offices/cpa/tstmny/index.htm",
  # TODO the highlights are years...

  "SPWP": "http://oig.state.gov/lbry/plans/index.htm",
  "O": "http://oig.state.gov/lbry/other/c26047.htm",
  "FOIA": "http://oig.state.gov/foia/readroom/index.htm",
  "PR": "http://oig.state.gov/lbry/other/c39666.htm",
  "P": "http://oig.state.gov/lbry/other/c26046.htm",
}

TOPIC_NAMES = {
  "A": "Audits",
  "I": "Inspections",
  "BBG": "Broadcasting Board of Governors",
  "IT": "Information Technology",
  "MA": "Management Alerts and Other Action Items",
  "SR": "Semiannual Reports to Congress",
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

NESTED_TOPICS = ["A", "I", "BBG"]

# TODO kill?
REPORT_ID_TO_PUBLISHED_ON = {
  # '197264': datetime.datetime(2012, 8, 1),
  # '196458': datetime.datetime(2012, 8, 10),
  # '169045': datetime.datetime(2011, 7, 12),
}

# TODO archives

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    topic_url = TOPIC_TO_URL[topic]
    topic_name = TOPIC_NAMES[topic]

    if topic in NESTED_TOPICS:
      subtopic_link_map = get_page_highlights(topic_url)
    else:
      # TODO
      subtopic_link_map = {None: topic_url}

    for subtopic_name, subtopic_url in subtopic_link_map.items():
      print(topic, subtopic_name, subtopic_url)
      logging.debug("## Processing subtopic %s" % subtopic_name)

      body = utils.download(subtopic_url)
      doc = BeautifulSoup(body)

      results = doc.select("#body-row02-col02andcol03 a")
      if not results:
        results = doc.select("#body-row02-col01andcol02andcol03 a")
      if not results:
        raise AssertionError("No report links found for %s" % landing_url)
      for result in results:
        report = report_from(result, topic_name, year_range)
        if report:
          inspector.save_report(report)

# suggested: construct URL based on options
def url_for(options, page = 1):
  pass

# suggested: a function that gets report details from a parent element,
# extract a dict of details that are ready for inspector.save_report().
def report_from(result, topic_name, year_range):
  title = result.text.strip()
  report_url = result['href']

  if ("archives" in title.lower()
      or 'foia' in title.lower()
      or 'foia' in report_url
      or report_url in [
        'http://oig.state.gov/lbry/sar/index.htm',
        'http://oig.state.gov/lbry/congress/index.htm'
        ]
    ):
    return None

  logging.debug("## Processing report %s" % report_url)

  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]

  try:
    previous_sibling_text = str(result.previous_sibling).strip()
  except AttributeError:
    previous_sibling_text = ""
  except TypeError:
    import pdb;pdb.set_trace()

  if report_id in REPORT_ID_TO_PUBLISHED_ON:
    published_on = REPORT_ID_TO_PUBLISHED_ON[report_id]
  else:
    try:
      published_on = datetime.datetime.strptime(previous_sibling_text, "-%m/%d/%y")
    except ValueError:
      try:
        published_on = datetime.datetime.strptime("-".join(title.split()[-2:]), "%b-%Y")
      except ValueError:
        try:
          # Fall back to when the report was posted to the site
          posted_text = result.find_parent("p").previous_sibling.previous_sibling.text
          published_on = datetime.datetime.strptime(posted_text, 'Posted %B %d, %Y')
        except ValueError:
          import pdb;pdb.set_trace()
        except AttributeError:
          import pdb;pdb.set_trace()

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  return {
    'inspector': 'state',
    'inspector_url': 'http://oig.state.gov/',
    'agency': 'state',
    'agency_name': 'Department of State',
    'report_id': report_id,
    'topic': topic_name,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

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
