#!/usr/bin/env python

import datetime
import logging
import os

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://oig.usaid.gov
# Oldest report: 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://oig.usaid.gov/auditandspecialbyyear?page={page}"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for page in range(0, 999):
    url = AUDIT_REPORTS_URL.format(page=page)
    doc = BeautifulSoup(utils.download(url))
    results = doc.select("li.views-row")
    if not results:
      break

    for result in results:
      report = report_from(result, url, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, year_range):
  link = result.find("a")

  if link:
    title = link.text
    report_url = link.get('href')
    unreleased = False
  else:
    title = result.select("div.views-field-title")[0].text
    report_url = None
    unreleased = True

  published_on_text = result.select("span.date-display-single")[0].text
  published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  try:
    report_id_text = result.select("div.views-field-field-auditreport-doc-data")[0].text.strip()
    report_id = "-".join(report_id_text.replace("/", "-").split())
  except IndexError:
    report_id = None

  if not report_id and report_url:
    report_filename = report_url.split("/")[-1]
    report_id, _ = os.path.splitext(report_filename)

  if not report_id:
    report_id = "{}-{}".format("-".join(title.split()), published_on_text)

  report_id = report_id.replace("/", "-")

  report = {
    'inspector': "aid",
    'inspector_url': "http://oig.usaid.gov",
    'agency': "aid",
    'agency_name': "Agency For International Development",
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
