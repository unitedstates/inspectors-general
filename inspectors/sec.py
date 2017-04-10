#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# http://www.sec.gov/about/offices/oig/inspector_general_reppubs_testimony.shtml
archive = 1994

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated, which
#            correspond to the topics defined on the site. For example:
#            'ISSUED_REPORTS,INVESTIGATIVE_REPORTS'
#            Defaults to all topics.
#
#            Topic codes are:
#            ISSUED_REPORTS           - Issued Reports
#            INVESTIGATIVE_REPORTS    - Investigative Reports
#            INVESTIGATIVE_MEMORANDA  - Investigative Memoranda
#            SEMIANNUAL_REPORTS       - Semiannual Reports
#            TESTIMONY                - Testimony
#            OTHER                    - Other
#
# Notes for IG's web team:
#   - All reports available on a single page/feed
#   - Add published dates for all https://www.sec.gov/foia/foiadocs.htm
#   - Consistent published date formats (Mar. 1, 2013 vs March 1, 2013)
#   - Consistent report format (some are html and some are PDFs)

# TODO: Probably want to grab more from https://www.sec.gov/foia/foiadocs.htm

TOPIC_TO_URL = {
  'ISSUED_REPORTS': 'https://www.sec.gov/about/offices/oig/inspector_general_audits_reports.shtml',
  'INVESTIGATIVE_REPORTS': 'https://www.sec.gov/about/offices/oig/inspector_general_investigations_reports.shtml',
  'INVESTIGATIVE_MEMORANDA': 'https://www.sec.gov/about/offices/oig/inspector_general_investigations_memoranda.shtml',
  'SEMIANNUAL_REPORTS': 'https://www.sec.gov/about/offices/oig/inspector_general_reppubs_semireports.shtml',
  'TESTIMONY': 'https://www.sec.gov/about/offices/oig/inspector_general_reppubs_testimony.shtml',
  'OTHER': 'https://www.sec.gov/about/offices/oig/inspector_general_reppubs_other.shtml',
}
BASE_REPORT_URL = "https://www.sec.gov"

TOPIC_TO_REPORT_TYPE = {
  'ISSUED_REPORTS': 'audit',
  'INVESTIGATIVE_REPORTS': 'investigation',
  'INVESTIGATIVE_MEMORANDA': 'investigation',
  'SEMIANNUAL_REPORTS': 'semiannual_report',
  'TESTIMONY': 'testimony',
  'OTHER': 'other',
}

# Some reports have bugs such that it is hard to find the published time.
# Hardcode these for now.
REPORT_URL_TO_PUBLISHED_DATETIMES = {
  "http://www.justice.gov/opa/pr/2011/March/11-crm-341.html": datetime.datetime(2011, 3, 16),
  "https://www.sec.gov/about/oig/audit/246fin.htm": datetime.datetime(1997, 1, 7),
  "https://www.sec.gov/about/offices/oig/reports/reppubs/other/finalpeerreviewreport-sec.pdf": datetime.datetime(2012, 8, 23),
  "https://www.sec.gov/about/offices/oig/reports/audits/2010/478.pdf": datetime.datetime(2010, 5, 7),
  "https://www.sec.gov/about/offices/oig/reports/reppubs/other/cpb_peerreview-sec.pdf": datetime.datetime(2010, 1, 22),
  "https://www.sec.gov/about/offices/oig/reports/reppubs/other/kotz_legislativerecommendationsforbankingcommittee.pdf": datetime.datetime(2009, 10, 29),
  "https://www.sec.gov/about/offices/oig/reports/reppubs/other/sec_oig_pressrelease_1_13.pdf": datetime.datetime(2012, 1, 13),
  "https://www.sec.gov/about/offices/oig/reports/reppubs/other/oig_strategicplan2010-2015-9-1-10-508.pdf": datetime.datetime(2010, 9, 1),
  "https://www.sec.gov/oig/reportspubs/Review-of-the-SECs-Pay-Transition-Program-15-ONR-0281-R-1-27-2016.pdf": datetime.datetime(2016, 1, 27),
  "https://www.sec.gov/oig/reportspubs/OIG-Strategic-Plan-for-Fiscal-Years-2017---2019.pdf": datetime.datetime(2016, 9, 19),
}

CANNED_REPORTS = [
  {
    'report_id': '271fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/271fin.htm',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'Property System',
    'published_on': '1998-09-25',
  },
  {
    'report_id': '384fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/384fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'Enforcement Disgorgement Waivers',
    'published_on': '2005-01-18',
  },
  {
    'report_id': '392fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/392fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'NERO IT Management',
    'published_on': '2005-02-14',
  },
  {
    'report_id': '394fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/394fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'Targeting BD Compliance Examinations',
    'published_on': '2005-09-22',
  },
  {
    'report_id': '398fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/398fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'Management of Wireless Communication Devices',
    'published_on': '2005-03-24',
  },
  {
    'report_id': '399fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/399fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'Government Performance & Results Act - 2004',
    'published_on': '2005-09-27',
  },
  {
    'report_id': '400fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/400fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'SERO IT Management',
    'published_on': '2005-03-24',
  },
  {
    'report_id': '406fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/406fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': '2005 FISMA Executive Summary Report',
    'published_on': '2005-09-23',
  },
  {
    'report_id': '409fin',
    'type': 'audit',
    'topic': 'ISSUED_REPORTS',
    'url': 'https://www.sec.gov/about/oig/audit/409fin.pdf',
    'landing_url': TOPIC_TO_URL['ISSUED_REPORTS'],
    'title': 'Security Certification and Accreditation of ACTS Plus',
    'published_on': '2005-09-30',
  },
]


def run(options):
  year_range = inspector.year_range(options, archive)
  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = list(TOPIC_TO_URL.keys())
    topics.sort()

  for topic in topics:
    topic_url = TOPIC_TO_URL[topic]
    doc = utils.beautifulsoup_from_url(topic_url)

    try:
      year_results = doc.select("#Listing")[0]
      results = [x for x in year_results.select("ul li ul li")]
    except IndexError:
      try:
        all_results = doc.select("#bodyholder")[0]
        results = [x for x in all_results.select("ul li")]
      except IndexError:
        results = doc.select(".main-content ul li")
    if not results:
      raise inspector.NoReportsFoundError("SEC (%s)" % topic)

    # Sometimes multiple reports are listed under the same datetime element.
    # We store which published datetime we saw last so that the next report
    # can use if if we are unable to find another published time.
    last_published_on = None
    for result in results:
      report, last_published_on = report_from(result, topic_url, topic, year_range, last_published_on)
      if report:
        inspector.save_report(report)

  for canned_report in CANNED_REPORTS:
    report_datetime = datetime.datetime.strptime(canned_report["published_on"], "%Y-%m-%d")
    if report_datetime.year in year_range:
      add_common_fields(canned_report)
      inspector.save_report(canned_report)


def report_from(result, landing_url, topic, year_range, last_published_on):
  try:
    report_link = result.select("a[href]")[0]
  except IndexError as exc:
    # There is a bug for this date where it does not have a report.
    # https://www.sec.gov/about/offices/oig/inspector_general_audits_reports.shtml
    if result.text.strip() == 'Jan. 7, 1997':
      return None, None
    else:
      raise exc

  report_url = urljoin(BASE_REPORT_URL, report_link['href'])

  # HTTPS, even if they haven't updated their links yet
  report_url = re.sub("^http://www.sec.gov", "https://www.sec.gov", report_url)

  logging.debug("### Processing report %s" % report_url)
  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]
  title = report_link.text.strip()
  report_type = TOPIC_TO_REPORT_TYPE[topic]

  text_lines = [line.strip() for line in result.text.split("\n")]
  text_lines = [line for line in text_lines if line]
  published_on_text = text_lines[0].split("through")[0].strip().replace(".", "")
  published_on = published_date_for_report(published_on_text, title, report_url, last_published_on, report_id)
  if not published_on:
    admin.log_no_date("sec", report_id, title, report_url)
    return None, None

  # Skip duplicate report
  if report_id == '283fin' and published_on.year == 1999 and published_on.month == 3 and published_on.day == 16:
    return None, published_on

  # Audit Memo No. 39 is posted in two locations,
  # https://www.sec.gov/about/offices/oig/reports/audits/2005/am39.pdf and
  # https://www.sec.gov/about/oig/audit/am39.pdf,
  # skip the second one
  if report_url == 'https://www.sec.gov/about/oig/audit/am39.pdf':
    return None, published_on

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return None, published_on

  logging.debug("### Processing report %s" % report_link)

  report = {
    'report_id': report_id,
    'type': report_type,
    'topic': topic,
    'url': report_url,
    'landing_url': landing_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  add_common_fields(report)
  return report, published_on


def add_common_fields(report):
  report['inspector'] = 'sec'
  report['inspector_url'] = 'http://www.sec.gov/about/offices/oig/inspector_general_investigations_reports.shtml'
  report['agency'] = 'sec'
  report['agency_name'] = 'Securities and Exchange Commission'


def find_first_matching_datetime_format_from_text(text_datetime_format_tuples):
  for text, datetime_format in text_datetime_format_tuples:
    try:
      return datetime.datetime.strptime(text, datetime_format)
    except ValueError:
      pass


def published_date_for_report(published_on_text, title, report_url, last_published_on, report_id):
  "There are multiple different ways we try to extract the published date"
  if report_url in REPORT_URL_TO_PUBLISHED_DATETIMES:
    return REPORT_URL_TO_PUBLISHED_DATETIMES[report_url]

  published_on = find_first_matching_datetime_format_from_text([
    (published_on_text, "%b %d, %Y"),
    (published_on_text, "%B %d, %Y"),

    # Try parsing date from the end of the title
    ("".join(title.split(",")[-2:]).strip(), "%B %d %Y"),
    (" ".join(title.split()[-2:]), '%B %Y'),

    # 'April 1, 2005 to September 30, 2005 Tables'
    (" ".join(title.rstrip(" Tables").split()[-3:]), '%B %d, %Y'),

    # https://www.sec.gov/oig/reportspubs/purchasecardabuseprevention_012714.pdf
    (os.path.splitext(report_url.split("_")[-1])[0], "%m%d%y"),

    # https://www.sec.gov/about/offices/oig/reports/reppubs/other/11-30-2012_memo-to-comm-re-postal-investigation-impact.pdf
    (os.path.basename(report_url).split("_")[0], "%m-%d-%Y"),
  ])

  # Sometimes, splitting on newlines does not work for extracting the date.
  # If we haven't found a date, try selecting one from the text with a regex.
  if not published_on:
    date_match = DATE_RE_1.search(published_on_text)
    if date_match:
      published_on_text = date_match.group(0).replace('.', '')
      published_on = find_first_matching_datetime_format_from_text([
        (published_on_text, '%b %d, %Y'),
        (published_on_text, '%B %d, %Y')
      ])

  if not published_on:
    date_match = DATE_RE_2.search(report_url)
    if date_match:
      published_on_text = date_match.group(1)
      published_on = find_first_matching_datetime_format_from_text([
        (published_on_text, '%m%d%y')
      ])

  if not published_on:
    published_on = last_published_on

  return published_on

DATE_RE_1 = re.compile('(?:January|Jan\\.?|February|Feb\\.?|March|Mar\\.?|'
                       'April|Apr\\.?|May\\.?|June|Jun\\.?|July|Jul\\.?|'
                       'August|Aug\\.?|September|Sept?\\.?|October|Oct\\.?|'
                       'November|Nov\\.?|December|Dec\\.?) [123]?[0-9], [0-9]{4}')
DATE_RE_2 = re.compile('[^0-9]([01][0-9][0-3][0-9][901][0-9])[^0-9]')

utils.run(run) if (__name__ == "__main__") else None
