#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.oig.dol.gov/auditreports.htm
# Oldest report: 1996

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Fix published date for "Audit of The National Council on the Aging, INC.".
# Right now it just says "February 11" without a year.

AGENCY_REPORTS_URL = "http://www.oig.dol.gov/cgi-bin/oa_rpts.cgi?s=&y=all&a={}"
SEMIANNUAL_REPORTS_URL = "http://oig.federalreserve.gov/reports/semiannual-report-to-congress.htm"

AGENCY_IDS = {
  "BILA": "01-070",
  "BLS": "11",
  "EBSA": "12",
  "ETA": "03",
  "MSHA": "06",
  "OSHA": "10",
  "OASAM": "07",
  "OCFO": "13",
  "ODEP": "01-080",
  "OFCCP": "04-410",
  "OLMS": "04-421",
  "OSE": "01",
  "OSO": "08",
  "OWC": "04-431",
  "TAA": "03-330",
  "VETS": "02",
  "WHD": "04-420",
  "WB": "01-020",
}
AGENCY_NAMES = {
  "BILA": "Bureau of International Labor Affairs",
  "BLS": "Bureau of Labor Statistics",
  "EBSA": "Employee Benefits Security Administration",
  "ETA": "Employment and Training Administration",
  "MSHA": "Mine Safety and Health Administration",
  "OSHA": "Occupational Safety and Health Administration",
  "OASAM": "Office of the Assistant Secretary for Administration and Management",
  "OCFO": "Office of the Chief Financial Officer",
  "ODEP": "Office of Disability Employment Policy",
  "OFCCP": "Office of Federal Contract Compliance Programs",
  "OLMS": "Office of Labor Management Standards",
  "OSE": "Office of the Secretary",
  "OSO": "Office of the Solicitor",
  "OWC": "Office of Workers Compensation",
  "TAA": "Trade Adjustment Assistance",
  "VETS": "Veterans' Employment and Training Service",
  "WHD": "Wage and Hour Division",
  "WB": "Women's Bureau",
}

REPORT_PUBLISHED_MAPPING = {
  "02-02-202-03-360": datetime.datetime(2002, 2, 11),
}

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for agency, agency_id in AGENCY_IDS.items():

    for offset in range(0, 10000, 20):
      agency_url = AGENCY_REPORTS_URL.format("{}&next_i={}".format(agency_id, offset))
      doc = beautifulsoup_from_url(agency_url)
      results = doc.select("ol li")
      if not results:
        break
      for result in results:
        report = report_from(result, agency, agency_url, year_range)
        if report:
          inspector.save_report(report)

  # Pull the semiannual reports
  # doc = beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  # results = doc.select("")
  # for result in results:
  #   report = semiannual_report_from(result, year_range)
  #   inspector.save_report(report)

def report_from(result, agency, agency_url, year_range):
  title = result.contents[0]
  landing_url = agency_url  # No real landing pages
  report_id_text, published_text = result.contents[2].split("(")
  report_id = report_id_text.replace("Report No.", "").strip()
  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    published_text = published_text.rstrip(")")
    date_formats = ["%B %d, %Y", "%B %Y"]
    for date_format in date_formats:
      published_on = datetime.datetime.strptime(published_text, date_format)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  if "This report contains Sensitive Information and will not be posted" in result.text:
    unreleased = True
  else:
    unreleased = False

  report_url, summary_url, response_url = None, None, None
  if not unreleased:
    for link in result.select("a"):
      if 'Report' in link.text:
        report_url = link.get('href')
      elif 'Summary' in link.text:
        summary_url = link.get('href')
      elif 'Response' in link.text:
        response_url = link.get('href')
    if report_url is None:
      if report_id == "24-08-004-03-330":
        unreleased = True
      else:
        import pdb;pdb.set_trace()

  report = {
    'inspector': 'labor',
    'inspector_url': 'http://www.oig.dol.gov',
    'agency': agency,
    'agency_name': AGENCY_NAMES[agency],
    'report_id': report_id,
    'url': report_url,
    'landing_url': landing_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if summary_url:
    report['summary_url'] = summary_url
  if response_url:
    report['response_url'] = response_url
  if unreleased:
    report['unreleased'] = unreleased
  return report

# def semiannual_report_from(result, year_range):
#   pass

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None