#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www.treasury.gov/tigta/publications_semi.shtml
# Oldest report: 1999

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Report https://www.treasury.gov/tigta/auditreports/2014reports/201310018fr.pdf is missing

# Ideally, we would use the 'No Script' urls (http://www.treasury.gov/tigta/oa_auditreports_fy08_noscript.shtml),
# but unfortunately some of those don't list all of the published dates that
# the actual js files list.
AUDITS_REPORTS_URL = "https://www.treasury.gov/tigta/oa_auditreports_fy{}.js"
INSPECTIONS_REPORTS_URL = "https://www.treasury.gov/tigta/oie_iereports_fy{}.js"

CONGRESSIONAL_TESTIMONY_REPORTS_URL = "https://www.treasury.gov/tigta/publications_congress.shtml"
SEMIANNUAL_REPORTS_URL = "https://www.treasury.gov/tigta/publications_semi.shtml"

BASE_REPORT_URL = "https://www.treasury.gov/tigta/"

MISSING_REPORT_IDS = [
  "201310018",
]

def run(options):
  year_range = inspector.year_range(options)

  # Pull the audit reports
  for year in year_range:
    url = audit_report_url(year)
    if url:
      parse_result_from_js_url(url, "auditreports", year, year_range)
    url = inspection_report_url(year)
    if url:
      parse_result_from_js_url(url, "iereports", year, year_range)

  # Pull the congressional testimony
  doc = beautifulsoup_from_url(CONGRESSIONAL_TESTIMONY_REPORTS_URL)
  results = doc.findAll("ul", type='disc')[0].select("li")
  for result in results:
    report = congressional_testimony_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.findAll("ul", type='disc')[0].select("li")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def parse_result_from_js_url(url, format_slug, year, year_range):
  """
  Given a link to a javascript file that has report data, add all of the reports
  """

  body = utils.download(url)
  # Pulling out javascript array values that look like:
  # arrid[0]=new AR("200720002","Stronger Management Oversight Is Required to Ensure Valuable Systems Modernization Expertise Is Received From the Federally Funded Research and Development Center Contractor","20061020","01",2,0,0,0);
  # Look in https://www.treasury.gov/tigta/oa_auditreports_fy14.js for some more examples.
  results = re.findall('arrid\[\d+\]=new AR\((.*)\);', body)
  for result in results:
    report = report_from(result, format_slug, year, year_range)
    if report:
      inspector.save_report(report)


def report_from(result, format_slug, year, year_range):
  # We are going to parse the script of javascript into a list of with the following strucutre:
  # [report id, report description, date string, business unit, report count, executive summary, management response, audit comments]
  result_pieces = [field.strip() for field in parse_fields(result)]
  report_id = result_pieces[0]
  title = result_pieces[1]
  published_on_text = result_pieces[2]

  published_on = datetime.datetime.strptime(published_on_text.replace('"', ''), '%Y%m%d')

  # This formatting is described more in https://www.treasury.gov/tigta/oa_auditreports_updated_fy14.js
  report_url = "https://www.treasury.gov/tigta/{}/{}reports/{}fr.pdf".format(format_slug, year, report_id)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  if report_id in MISSING_REPORT_IDS:
    return

  report = {
    'inspector': 'tigta',
    'inspector_url': 'https://www.treasury.gov/tigta/',
    'agency': 'irs',
    'agency_name': 'Internal Revenue Service',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def congressional_testimony_report_from(result, year_range):
  report_url = urljoin(BASE_REPORT_URL, result.find("a").get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)
  title = result.contents[1].lstrip(" -")

  published_on_text = result.select("b")[0].text
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'tigta',
    'inspector_url': 'https://www.treasury.gov/tigta/',
    'agency': 'irs',
    'agency_name': 'Internal Revenue Service',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, year_range):
  report_url = urljoin(BASE_REPORT_URL, result.find("a").get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on_text_range = result.contents[0]
  published_on_text = published_on_text_range.split(" - ")[1]
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  title = "Semiannual Report {}".format(published_on_text_range)

  report = {
    'inspector': 'tigta',
    'inspector_url': 'https://www.treasury.gov/tigta/',
    'agency': 'irs',
    'agency_name': 'Internal Revenue Service',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def audit_report_url(year):
  if year < 2004: ## The earliest year for these reports
    return None
  last_year_digits = str(year)[2:]  # Grab the last two digits
  return AUDITS_REPORTS_URL.format(last_year_digits)

def inspection_report_url(year):
  if year < 2008: ## The earliest year for these reports
    return None
  last_year_digits = str(year)[2:]  # Grab the last two digits
  return INSPECTIONS_REPORTS_URL.format(last_year_digits)

def parse_fields(text):  # Taken from https://stackoverflow.com/a/4983565
    """
    >>> list(parse_fields('hey,hello,,"hello,world",\'hey,world\''))
    ['hey', 'hello', '', 'hello,world', 'hey,world']
    >>> list(parse_fields('hey,hello,,"hello,world",\'hey,world\','))
    ['hey', 'hello', '', 'hello,world', 'hey,world', '']
    >>> list(parse_fields(',hey,hello,,"hello,world",\'hey,world\','))
    ['', 'hey', 'hello', '', 'hello,world', 'hey,world', '']
    >>> list(parse_fields(''))
    ['']
    >>> list(parse_fields(','))
    ['', '']
    >>> list(parse_fields('testing,quotes not at "the" beginning \'of\' the,string'))
    ['testing', 'quotes not at "the" beginning \'of\' the', 'string']
    >>> list(parse_fields('testing,"unterminated quotes'))
    ['testing', '"unterminated quotes']
    """
    pos = 0
    exp = re.compile(r"""(['"]?)(.*?)\1(,|$)""")
    while True:
        m = exp.search(text, pos)
        result = m.group(2)
        separator = m.group(3)

        yield result

        if not separator:
            break

        pos = m.end(0)

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)

utils.run(run) if (__name__ == "__main__") else None
