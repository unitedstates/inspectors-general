#!/usr/bin/env python

import datetime
import re
import logging
from urllib.parse import urljoin, urlparse
import os

from utils import utils, inspector

# http://www.cpb.org/oig/
archive = 2010

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#
#   Include the "Issued <Month> <Day>, <Year>" text for every report (in the <li> tag)
#   Standardize the report file names, and include the year, month, and day consistently.
#

AUDIT_REPORTS_URL = "http://www.cpb.org/oig/reports/"
OTHER_REPORTS_URL = "http://www.cpb.org/oig/other-reports"

ISSUED_DATE_EXTRACTION = re.compile('[A-Z][a-z]+ \d{1,2}, \d{4}')

REPORT_ID_DATE_EXTRACTION = [
  re.compile('.*(?P<month>\d{2})(?P<day>\d{2})(?P<year_2>\d{2})$'),
  re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[-_].*$'),
  re.compile('OIGPeerReview-(?P<year>\d{4})-(?P<month_name>\w+)$'),
  re.compile('^(?P<month_and_year>\d{3,4})_'),
  re.compile('^annualplan(?P<year_2>\d{2})$'),
  re.compile('^Strategic-Plan-(?P<year>\d{4})-\d{4}$'),
]

REPORT_PUBLISHED_MAP = {
  "606_EvaluationCPBResponse": datetime.datetime(2006, 6, 9),
  "602_cpb_ig_reportofreview": datetime.datetime(2005, 11, 15),
  "OIGPeerReview-2013-September": datetime.datetime(2013, 9, 27),
  "annualplan16": datetime.datetime(2015, 10, 14),
  "annualplan15": datetime.datetime(2014, 10, 17),
  "annualplan14": datetime.datetime(2013, 9, 17),
  "Strategic-Plan-2014-2018": datetime.datetime(2013, 8, 22),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  doc = utils.beautifulsoup_from_url(AUDIT_REPORTS_URL)
  rows = doc.select("div.content > div > div > div > div.row")
  row_audits = rows[0]

  # Audit reports
  results = row_audits.select("ul li.pdf")
  if not results:
    raise inspector.NoReportsFoundError("CPB (audits)")
  for result in results:
    report = report_from(result, AUDIT_REPORTS_URL, "audit", year_range)
    if report:
      inspector.save_report(report)

  doc = utils.beautifulsoup_from_url(OTHER_REPORTS_URL)
  rows = doc.select("div.content > div > div > div > div.row")
  row_peer_review = rows[0]
  col_plans = rows[1].select("div.col-md-6")[0]
  col_congress = rows[1].select("div.col-md-6")[1]

  # Peer review
  results = row_peer_review.select("ul li.pdf")
  if not results:
    raise inspector.NoReportsFoundError("CPB (peer reviews)")
  for result in results:
    report = report_from(result, OTHER_REPORTS_URL, "other", year_range)
    if report:
      inspector.save_report(report)

  # Plans
  results = col_plans.select("ul li.pdf")
  if not results:
    raise inspector.NoReportsFoundError("CPB (plans)")
  for result in results:
    report = report_from(result, OTHER_REPORTS_URL, "other", year_range)
    if report:
      inspector.save_report(report)

  # Semiannual reports to congress
  results = col_congress.select("ul li.pdf")
  if not results:
    raise inspector.NoReportsFoundError("CPB (semiannual reports)")
  for result in results:
    report = report_from(result, OTHER_REPORTS_URL, "semiannual_report", year_range)
    if report:
      inspector.save_report(report)


def report_from(result, landing_url, report_type, year_range):
  link = result.find('a')
  report_url = urljoin(landing_url, link['href'])
  report_id = os.path.basename(urlparse(report_url)[2]).rstrip('.pdf')

  title = link.text
  if 'semiannual' in report_id:
    title = "Semi-Annual Report: %s" % title

  if title == "Report in Brief":
    # Skip report in brief after a full report
    return

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    issued_strong = result.parent.parent.parent.find("strong", text="Issued")
    if issued_strong:
      issued_on = ISSUED_DATE_EXTRACTION.search(issued_strong.parent.text)
      if issued_on:
        date_fmt = "%B %d, %Y"
        published_on = datetime.datetime.strptime(issued_on.group(0), date_fmt)

  if not published_on:
    published_on = extract_date_from_report_id(report_id)

  if not published_on:
    inspector.log_no_date(report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'cpb',
    'inspector_url': 'http://www.cpb.org/oig/',
    'agency': 'cpb',
    'agency_name': 'Corporation for Public Broadcasting',
    'file_type': 'pdf',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'unreleased': False,
  }

  return report

def extract_date_from_report_id(report_id):
  published_on = ''

  for prog in REPORT_ID_DATE_EXTRACTION:
    match = prog.match(report_id)
    if match:

      year = ''
      month = ''
      day = ''

      try:
        month_and_year = match.group('month_and_year')
        if len(month_and_year) == 3:
          month = '0%s' % month_and_year[0]
          year = '20%s' % month_and_year[1:]
        elif len(month_and_year) == 4:
          month = '%s' % month_and_year[0:2]
          year = '20%s' % month_and_year[2:]
      except IndexError:
        try:
          year = '20%s' % match.group('year_2')
        except IndexError:
          year = match.group('year')

        try:
          month = datetime.datetime.strptime(match.group('month_name'), '%B').strftime('%m')
        except IndexError:
          try:
            month = match.group('month')
          except IndexError:
            return None

      day = ''
      try:
        day = match.group('day')
      except IndexError:
        return None

      date_string = '%s-%s-%s' % (year, month, day)
      published_on = datetime.datetime.strptime(date_string, '%Y-%m-%d')

  return published_on

utils.run(run) if (__name__ == "__main__") else None
