#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector

# http://oig.tva.gov
archive = 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://oig.tva.gov/reports.html"
SEMIANNUAL_REPORTS_URL = "http://oig.tva.gov/sar_reports.html"
PEER_REVIEW_REPORTS_URL = "http://oig.tva.gov/peer_reports.html"

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  doc = utils.beautifulsoup_from_url(AUDIT_REPORTS_URL)
  for year in year_range:
    if year < 2005:  # This is the earliest audits go back
      continue
    results = doc.find(id=str(year)).select(".panel")
    if not results:
      raise inspector.NoReportsFoundError("Tennessee Valley Authority (%d)" % year)
    for result in results:
      report = audit_report_from(result, AUDIT_REPORTS_URL, year_range)
      if report:
        inspector.save_report(report)

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select(".tab-content .row")
  if not results:
    raise inspector.NoReportsFoundError("Tennessee Valley Authority (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the peer review reports
  doc = utils.beautifulsoup_from_url(PEER_REVIEW_REPORTS_URL)
  results = doc.select(".tab-content .row")
  if not results:
    raise inspector.NoReportsFoundError("Tennessee Valley Authority (peer review reports)")
  for result in results:
    report = peer_review_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def audit_report_from(result, landing_url, year_range):
  header = result.select(".panel-heading")[0]

  published_on_text, title, report_id = header.text.split("-", 2)

  # Some reports list multiple dates. Split on '&' to get the latter.
  published_on_text = published_on_text.split("&")[-1].strip()
  published_on_text = published_on_text.replace("NSeptember", "September")
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  title = re.sub("\\s+", " ", title)
  report_id = report_id.strip().replace("/", "-").replace(":", "")

  if "summary only" in result.text.lower():
    unreleased = True
    report_url = None
  else:
    unreleased = False
    link = result.find("a", href=lambda h: h and not h.startswith("#"))
    report_url = urljoin(landing_url, link['href'])

  summary_text = result.find("div", class_="panel-body").text
  summary = re.sub("\\s+", " ", summary_text)

  report = {
    'inspector': 'tva',
    'inspector_url': 'http://oig.tva.gov',
    'agency': 'tva',
    'agency_name': 'Tennessee Valley Authority',
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'summary': summary,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

def semiannual_report_from(result, year_range):
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result.a["href"])
  report_filename = os.path.basename(report_url)
  report_id, _ = os.path.splitext(report_filename)

  published_on_text = result.select(".info .title")[0].text
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Semiannual Report {}".format(published_on_text)
  alternative_title = result.select(".info .brief-description")[0].text.strip()
  if alternative_title:
    title = "{} ({})".format(alternative_title, title)
  summary = result.p.text.strip()

  report = {
    'inspector': 'tva',
    'inspector_url': 'http://oig.tva.gov',
    'agency': 'tva',
    'agency_name': 'Tennessee Valley Authority',
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'summary': summary,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def peer_review_report_from(result, year_range):
  report_url = urljoin(PEER_REVIEW_REPORTS_URL, result.a["href"])
  report_filename = os.path.basename(report_url)
  report_id, _ = os.path.splitext(report_filename)

  published_on_text = result.select(".info .title")[0].text
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Peer Review Report {}".format(published_on_text)
  summary = result.find("div", class_="info").find_next_sibling("p").text
  summary = summary.strip()

  report = {
    'inspector': 'tva',
    'inspector_url': 'http://oig.tva.gov',
    'agency': 'tva',
    'agency_name': 'Tennessee Valley Authority',
    'type': 'peer_review',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'summary': summary,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
