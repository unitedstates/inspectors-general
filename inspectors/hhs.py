#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
import string
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://oig.hhs.gov/reports-and-publications/index.asp
# Oldest report: TODO

# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated, which
#            correspond to the topics defined on the site. For example:
#            'OAS,OE'
#            Defaults to all topics.
#
#            OAS  - Office of Audit Services
#            OE   - Office of Evaluation and Inspections
#            HCF  - Health Care Fraud and Abuse Control Program Report
#            SAR  - Semiannual Reports to Congress
#            MIR  - Medicaid Integrity Reports
#            TMPC - Top Management & Performance Challenges
#            CPR  - Compendium of Priority Recommendations
#            SP   - Strategic Plan
#            WP   - Work Plan
#            POR  - Portfolio and Other Reports
#            FOIA - Freedom of Information Act (FOIA)
#            FRN  - Federal Register Notices
#            RA   - Regulatory Authorities
#            B    - OIG Budget
#            RAOR - Recovery Act Oversight Reports
#            RAA  - Recovery Act-related Audit and Inspection Reports
#            O    - GAO Forum Highlights Report: Data Analytics For Oversight

# Notes for IG's web team:
#  - Fix published date for http://oig.hhs.gov/oas/reports/region3/31200010.asp
#  on http://oig.hhs.gov/reports-and-publications/oas/cms.asp. It currently
#  says 08-03-2102

# TODO archives
# See archive link on https://oig.hhs.gov/reports-and-publications/oas/acf.asp

TOPIC_TO_URL = {
  "OAS": 'https://oig.hhs.gov/reports-and-publications/oas/index.asp',
  # "OE": 'https://oig.hhs.gov/reports-and-publications/oei/subject_index.asp',
  "HCF": 'https://oig.hhs.gov/reports-and-publications/hcfac/index.asp',
  "SAR": 'https://oig.hhs.gov/reports-and-publications/semiannual/index.asp',
  "MIR": 'https://oig.hhs.gov/reports-and-publications/medicaid-integrity/index.asp',
  "TMPC": 'https://oig.hhs.gov/reports-and-publications/top-challenges/',
  "CPR": 'https://oig.hhs.gov/reports-and-publications/compendium/index.asp',
  "SP": 'https://oig.hhs.gov/reports-and-publications/strategic-plan/index.asp',
  "WP": 'https://oig.hhs.gov/reports-and-publications/workplan/index.asp',
  "POR": 'https://oig.hhs.gov/reports-and-publications/portfolio/index.asp',
  "FOIA": 'https://oig.hhs.gov/reports-and-publications/foia/index.asp',
  "FRN": 'https://oig.hhs.gov/reports-and-publications/federal-register-notices/index.asp',
  "RA": 'https://oig.hhs.gov/reports-and-publications/regulatory-authorities/index.asp',

  # "B": 'https://oig.hhs.gov/reports-and-publications/budget/index.asp',
  # "RAOR": 'https://oig.hhs.gov/reports-and-publications/recovery/index.asp',
  "RAA": 'https://oig.hhs.gov/reports-and-publications/recovery/recovery_reports.asp',
  # "O": 'https://oig.hhs.gov/reports-and-publications/other/gao.asp',
}

TOPIC_NAMES = {
  "OAS": 'Office of Audit Services',
  "OE": 'Office of Evaluation and Inspections',
  "HCF": 'Health Care Fraud and Abuse Control Program Report ',
  "SAR": 'Semiannual Reports to Congress',
  "MIR": 'Medicaid Integrity Reports',
  "TMPC": 'Top Management & Performance Challenges',
  "CPR": 'Compendium of Priority Recommendations',
  "SP": 'Strategic Plan',
  "WP": 'Work Plan',
  "POR": 'Portfolio and Other Reports',
  "FOIA": 'Freedom of Information Act (FOIA)',
  "FRN": 'Federal Register Notices',
  "RA": 'Regulatory Authorities',
  "B": 'OIG Budget',
  "RAOR": 'Recovery Act Oversight Reports',
  "RAA": 'Recovery Act-related Audit and Inspection Reports',
  "O": 'GAO Forum Highlights Report: Data Analytics For Oversight',
}

TOPIC_WITH_SUBTOPICS = ['OAS']

ALPHABETICALLY_PAGED_TOPICS = ['OE']

REPORT_URL_MAPPING = {
  "https://oig.hhs.gov/reports-and-publications/medicaid-integrity/2011/": "https://oig.hhs.gov/reports-and-publications/medicaid-integrity/2011/medicaid_integrity_reportFY11.pdf"
}

REPORT_PUBLISHED_MAPPING = {
  "31200010": datetime.datetime(2012, 8, 3),
  'OIG-Strategic-Plan-2014-2018': datetime.datetime(2014, 1, 1),
}

# These are links that appear like reports, but are not.
BLACKLIST_REPORT_URLS = [
  'http://get.adobe.com/reader/'
]

BASE_URL = "https://oig.hhs.gov"

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    extract_reports_for_topic(topic, year_range)

def extract_reports_for_topic(topic, year_range):
  if topic in TOPIC_WITH_SUBTOPICS:
    subtopic_map = get_subtopic_map(topic)
  else:
    subtopic_map = {None: TOPIC_TO_URL[topic]}

  topic_name = TOPIC_NAMES[topic]
  for subtopic_name, subtopic_url in subtopic_map.items():
    logging.debug("## Processing subtopic %s" % subtopic_name)
    extract_reports_for_subtopic(subtopic_url, year_range, topic_name, subtopic_name)

def extract_reports_for_subtopic(subtopic_url, year_range, topic_name, subtopic_name):
  doc = beautifulsoup_from_url(subtopic_url)

  results = None
  if topic_name == 'Top Management & Performance Challenges':
    results = doc.select("#leftContentInterior > p > a")
  if not results:
    results = doc.select("#leftContentInterior dl dd")
  if not results:
    results = doc.select("#leftContentInterior > ul > li")
  if not results:
    results = doc.select("#leftContentInterior > p > a")
  if not results:
    import pdb;pdb.set_trace()
  for result in results:
    if result.parent.parent.attrs.get('id') == 'related':
      continue
    report = report_from(result, year_range, topic_name, subtopic_name)
    if report:
      inspector.save_report(report)

def report_from(result, year_range, topic, subtopic=None):
  if result.name == 'a':
    # Sometime we already have a link
    result_link = result
  else:
    result_link = result.find("a")

  try:
    report_url = urljoin(BASE_URL, result_link['href'])
  except TypeError:
    import pdb;pdb.set_trace()

  if report_url in REPORT_URL_MAPPING:
    report_url = REPORT_URL_MAPPING[report_url]

  if report_url in BLACKLIST_REPORT_URLS:
    return

  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]
  title = result_link.text

  if title == 'Read the Summary':
    # If there is a summary
    return

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    try:
      published_on_text = result.find_previous("dt").text.strip()
      published_on = datetime.datetime.strptime(published_on_text, "%m-%d-%Y")
    except (ValueError, AttributeError):
      try:
        fiscal_year = int(result.text.split(":")[0].split()[1])
        published_on = datetime.datetime(fiscal_year + 1, 1, 1)
      except (ValueError, IndexError):
        try:
          fiscal_year = int(report_filename.split("-")[0])
          published_on = datetime.datetime(fiscal_year + 1, 1, 1)
        except ValueError:
          try:
            published_on = datetime.datetime.strptime(title.replace(": ", ":"), "Compendium:%B %Y Edition")
          except ValueError:
            try:
              published_on = datetime.datetime.strptime(report_id.split("-")[-1], "%m%d%Y")
            except ValueError:
              try:
                report_year = int(report_url.split("/")[-2:-1][0])
                published_on = datetime.datetime(report_year, 1, 1)
              except (ValueError, IndexError):
                if "Fiscal Year" in title:
                  fiscal_year = int(title.replace("Fiscal Year ", ""))
                  published_on = datetime.datetime(fiscal_year + 1, 1, 1)
                else:
                  import pdb;pdb.set_trace()

  if published_on.year not in year_range:
    import pdb;pdb.set_trace()
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  result = {
    'inspector': 'hhs',
    'inspector_url': 'https://oig.hhs.gov/',
    'agency': 'hhs',
    'agency_name': 'Health & Human Services',
    'report_id': report_id,
    'topic': topic,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if subtopic:
    result['subtopic'] = subtopic
  return result

def get_subtopic_map(topic):
  topic_url = TOPIC_TO_URL[topic]

  # if topic in ALPHABETICALLY_PAGED_TOPICS:
  #   topic_url_without_trailing_path = topic_url.rsplit("/", 1)[0]
  #   return {None: urljoin(topic_url_without_trailing_path, letter) for letter in string.ascii_lowercase}

  body = utils.download(topic_url)
  doc = BeautifulSoup(body)

  return {
    link.text: urljoin(BASE_URL, link['href'])
    for link
    in doc.select("#leftContentInterior li a")
  }

def beautifulsoup_from_url(url):
  body = utils.download(url)
  doc = BeautifulSoup(body)

  # Some of the pages will return meta refreshes
  if doc.find("meta") and doc.find("meta").attrs.get('http-equiv') == 'REFRESH':
    redirect_url = urljoin(BASE_URL, doc.find("meta").attrs['content'].split("url=")[1])
    return beautifulsoup_from_url(redirect_url)
  else:
    return doc

utils.run(run) if (__name__ == "__main__") else None
