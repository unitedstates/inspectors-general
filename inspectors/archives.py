#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://www.archives.gov/oig/
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - List more than the most recent peer review

AUDIT_REPORTS_URL = "https://www.archives.gov/oig/reports/audit-reports-{year}.html"
SEMIANNUAL_REPORTS_URL = "https://www.archives.gov/oig/reports/semiannual-congressional.html"
PEER_REVIEWS_URL = "https://www.archives.gov/oig/reports/peer-review-reports.html"

REPORT_PUBLISHED_MAP = {
  "peer-review-2014": datetime.datetime(2014, 4, 30),
  "audit-report-10-01": datetime.datetime(2009, 10, 26),
  "audit-report-10-02": datetime.datetime(2009, 12, 11),
  "advisory-report-10-03": datetime.datetime(2010, 1, 28),
  "audit-report-10-04": datetime.datetime(2010, 4, 2),
  "audit-report-10-05": datetime.datetime(2010, 8, 18),
  "management-letter-10-06": datetime.datetime(2010, 3, 15),
  "audit-report-10-07": datetime.datetime(2010, 4, 28),
  "management-letter-10-08": datetime.datetime(2010, 3, 24),
  "audit-report-10-09": datetime.datetime(2010, 5, 27),
  "management-letter-10-10": datetime.datetime(2010, 4, 23),
  "advisory-report-10-11": datetime.datetime(2010, 4, 29),
  "advisory-report-10-12": datetime.datetime(2010, 5, 5),
  "audit-report-10-13": datetime.datetime(2010, 7, 15),
  "audit-report-10-14": datetime.datetime(2010, 8, 6),
  "audit-report-10-15": datetime.datetime(2010, 6, 23),
  "audit-report-10-16": datetime.datetime(2010, 8, 18),
  "management-letter-10-18": datetime.datetime(2010, 9, 16),
  "audit-report-10-19": datetime.datetime(2010, 9, 29),
  "management-letter-oi-10-01": datetime.datetime(2010, 3, 2),
  "management-letter-oi-10-02": datetime.datetime(2010, 1, 1),
  "management-letter-oi-10-03": datetime.datetime(2010, 5, 13),
  "audit-report-11-01": datetime.datetime(2010, 10, 29),
  "audit-report-11-02": datetime.datetime(2010, 10, 18),
  "audit-report-11-03": datetime.datetime(2011, 2, 16),
  "audit-report-11-04": datetime.datetime(2010, 11, 12),
  "audit-report-11-05": datetime.datetime(2011, 2, 18),
  "audit-report-11-06": datetime.datetime(2010, 11, 30),
  "audit-report-11-07": datetime.datetime(2011, 3, 22),
  "mgmt-letter-11-08": datetime.datetime(2011, 1, 5),
  "audit-report-11-09": datetime.datetime(2011, 1, 31),
  "audit-report-11-10": datetime.datetime(2011, 3, 8),
  "audit-report-11-11": datetime.datetime(2011, 3, 18),
  "mgmt-letter-11-12": datetime.datetime(2011, 5, 4),
  "mgmt-letter-11-13": datetime.datetime(2011, 6, 15),
  "audit-report-11-14": datetime.datetime(2011, 7, 7),
  "audit-report-11-15": datetime.datetime(2011, 7, 7),
  "audit-report-11-16": datetime.datetime(2011, 7, 15),
  "audit-report-11-17": datetime.datetime(2011, 9, 30),
  "mgmt-letter-11-18": datetime.datetime(2011, 8, 2),
  "mgmt-letter-11-19": datetime.datetime(2011, 8, 11),
  "audit-report-11-20": datetime.datetime(2011, 9, 30),
  "mgmt-letter-11-21": datetime.datetime(2011, 1, 1),
  "mgmt-letter-OI-11-01": datetime.datetime(2011, 6, 28),
  "mgmt-letter-12-01": datetime.datetime(2011, 10, 13),
  "audit-report-12-02": datetime.datetime(2012, 1, 1),
  "audit-report-12-03": datetime.datetime(2011, 11, 14),
  "advisory-report-12-04": datetime.datetime(2012, 1, 30),
  "audit-report-12-05": datetime.datetime(2012, 3, 27),
  "mgmt-letter-12-06": datetime.datetime(2012, 2, 21),
  "audit-memo-12-07": datetime.datetime(2012, 2, 23),
  "advisory-report-12-08": datetime.datetime(2012, 3, 30),
  "audit-report-12-09": datetime.datetime(2012, 5, 10),
  "audit-report-12-10": datetime.datetime(2012, 9, 13),
  "audit-report-12-11": datetime.datetime(2012, 1, 1),
  "audit-report-12-12": datetime.datetime(2012, 6, 5),
  "mgmt-letter-12-13": datetime.datetime(2012, 5, 22),
  "audit-report-12-14": datetime.datetime(2012, 9, 11),
  "audit-report-12-15": datetime.datetime(2012, 7, 23),
  "management-letter-12-16": datetime.datetime(2012, 9, 28),
  "audit-report-12-17": datetime.datetime(2012, 8, 27),
  "mgmt-letter-12-18": datetime.datetime(2012, 7, 30),
  "system-review-report-12-19": datetime.datetime(2012, 9, 27),
  "audit-report-13-01": datetime.datetime(2012, 12, 10),
  "audit-report-13-03": datetime.datetime(2013, 2, 15),
  "audit-report-13-05": datetime.datetime(2012, 12, 10),
  "audit-memorandum-13-06": datetime.datetime(2013, 1, 31),
  "advisory-report-13-07": datetime.datetime(2013, 1, 31),
  "audit-report-13-08": datetime.datetime(2013, 7, 9),
  "audit-report-13-09": datetime.datetime(2013, 7, 9),
  "audit-memorandum-13-10": datetime.datetime(2013, 7, 19),
  "audit-report-13-11": datetime.datetime(2013, 9, 19),
  "audit-report-13-12": datetime.datetime(2013, 9, 10),
  "audit-report-13-14": datetime.datetime(2013, 9, 18),
  "audit-memorandum-13-15": datetime.datetime(2013, 9, 25),
  "management-letter-13-02": datetime.datetime(2012, 10, 18),
  "management-letter-13-04": datetime.datetime(2012, 12, 4),
  "management-letter-13-13": datetime.datetime(2013, 7, 29),
  "audit-report-14-01": datetime.datetime(2014, 1, 30),
  "audit-report-14-03": datetime.datetime(2014, 1, 15),
  "audit-report-14-04": datetime.datetime(2014, 3, 5),
  "audit-report-14-05": datetime.datetime(2014, 3, 11),
  "audit-report-14-07": datetime.datetime(2014, 4, 2),
  "audit-report-14-08": datetime.datetime(2014, 4, 17),
  "audit-report-14-09": datetime.datetime(2014, 5, 1),
  "audit-report-14-10": datetime.datetime(2014, 5, 9),
  "audit-report-14-11": datetime.datetime(2014, 5, 5),
  "audit-report-14-12": datetime.datetime(2014, 7, 3),
  "advisory-report-14-14": datetime.datetime(2014, 6, 25),
  "mgmt-letter-14-02": datetime.datetime(2014, 1, 9),
  "mgmt-letter-14-06": datetime.datetime(2014, 1, 1),
  "mgmt-letter-14-17": datetime.datetime(2014, 8, 20),
  "mgmt-letter-14-18": datetime.datetime(2014, 9, 11),
  "audit-memorandum-14-13": datetime.datetime(2014, 5, 17),
  "audit-report-15-01": datetime.datetime(2014, 10, 27),
  "audit-report-15-02": datetime.datetime(2014, 11, 12),
  "audit-report-15-03": datetime.datetime(2015, 2, 6),
  "advisory-report-15-04": datetime.datetime(2014, 12, 11),
  "audit-report-15-05": datetime.datetime(2014, 12, 19),
  "audit-report-15-06": datetime.datetime(2015, 2, 10),
  "audit-report-15-10": datetime.datetime(2015, 3, 30),
  "audit-report-15-11": datetime.datetime(2015, 5, 5),
  "audit-report-15-12": datetime.datetime(2015, 5, 26),
  "audit-report-15-13": datetime.datetime(2015, 8, 24),
  "audit-report-15-14": datetime.datetime(2015, 9, 29),
  "mgmt-letter-15-09": datetime.datetime(2015, 2, 25),
  "audit-memo-15-07": datetime.datetime(2015, 1, 13),
  "audit-memo-15-08": datetime.datetime(2015, 2, 12),
}

def run(options):
  year_range = inspector.year_range(options, archive)
  results_flag = False

  # Pull the audit reports
  for year in year_range:
    if year < 2006:  # The oldest year for audit reports
      continue
    url = AUDIT_REPORTS_URL.format(year=year)
    doc = utils.beautifulsoup_from_url(url)
    if not doc:
      # Maybe page for current year hasn't been created yet
      continue
    results = doc.select("div#content li")
    if results:
      results_flag = True
    for result in results:
      report = audit_report_from(result, url, year, year_range)
      if report:
        inspector.save_report(report)

  if not results_flag:
    raise inspector.NoReportsFoundError("National Archives and Records Administration audit reports")

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("div#content li")
  if not results:
    raise inspector.NoReportsFoundError("National Archives and Records Administration semiannual reports")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the Peer Review
  doc = utils.beautifulsoup_from_url(PEER_REVIEWS_URL)
  result = doc.find("div", id='content').find("a", text=True)
  report = peer_review_from(result, year_range)
  if report:
    inspector.save_report(report)

def audit_report_from(result, landing_url, year, year_range):
  link = result.find("a")

  report_url = urljoin(landing_url, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  try:
    title = result.select("blockquote")[0].contents[0]
  except IndexError:
    title = result.text

  title_prefixer = re.compile("(Advisory|Management|Audit)\\s*(Letter|Report)\\s*[\\d\\-]+:\\s*", re.I)
  title = title_prefixer.sub("", title)

  estimated_date = False
  published_on = None

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  cleaned_text = re.sub("\s+", " ", inspector.sanitize(result.text))
  if not published_on:
    try:
      published_on_text = re.search('(\w+ \d+, \d+)', cleaned_text).groups()[0]
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except AttributeError:
      pass

  if not published_on:
    try:
      published_on_text = re.search('(\w+ \d+ , \d+)', cleaned_text).groups()[0]
      published_on = datetime.datetime.strptime(published_on_text, '%B %d , %Y')
    except AttributeError:
      pass

  if not published_on:
    try:
      response = utils.scraper.request(method="HEAD", url=report_url)
      last_modified = response.headers["Last-Modified"]
      published_on = datetime.datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
      pass

  if not published_on:
    admin.log_no_date("archives", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'archives',
    'inspector_url': 'https://www.archives.gov/oig/',
    'agency': 'archives',
    'agency_name': 'National Archives and Records Administration',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': 'audit',
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

def semiannual_report_from(result, year_range):
  link = result.find("a")

  report_url = urljoin(SEMIANNUAL_REPORTS_URL, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  title = result.text.strip()
  published_on = datetime.datetime.strptime(title, '%B %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'archives',
    'inspector_url': 'https://www.archives.gov/oig/',
    'agency': 'archives',
    'agency_name': 'National Archives and Records Administration',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': 'semiannual_report',
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def peer_review_from(result, year_range):
  report_url = urljoin(PEER_REVIEWS_URL, result.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    admin.log_no_date("archives", report_id, result.text, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Peer Review {}".format(published_on.year)

  report = {
    'inspector': 'archives',
    'inspector_url': 'https://www.archives.gov/oig/',
    'agency': 'archives',
    'agency_name': 'National Archives and Records Administration',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': 'peer_review',
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
