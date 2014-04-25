#!/usr/bin/env python

import datetime
from urlparse import urljoin
import re

from bs4 import BeautifulSoup

from utils import utils, inspector

# This script's "run" function will be run.
# You can do anything you want that eventually results in calling:
#
#   inspector.save_report(report)
#
# Where report is a dict with the following required fields:
#
#   inspector: the handle you chose for the IG, e.g. "usps"
#   agency: the agency the report relates to.
#           This can be the same value as the inspector field, but it
#           may differ -- some IGs monitor multiple agencies.
#   report_id: a unique ID for the report
#   title: title of report
#   url: link to report
#   published_on: date of publication
#   year: year of publication
#   file_type: 'pdf' or other file extension
#
# Any additional fields are fine, and will be kept.
#
# options:
#   since - date (YYYY-MM-DD) to fetch reports from.
#           defaults to 60 days ago.
#   pages - number of pages to fetch. defaults to 1.
#   only - limit reports fetched to one or more topic area, comma-separated.
#          e.g. "EF,IRM".
#          topic area codes are:
#          A    - Air
#          CB   - Chesapeake Bay
#          CC   - Climate Change
#          C    - Contracts
#          CO   - Counsel
#          X    - Cross-Media
#          DWG  - Domestic Working Group
#          EF   - Efficiency
#          E    - Enforcement
#          FM   - Financial Management
#          FA   - Forensic Audits
#          G    - Grants
#          GU   - Gulf Coast Oil Spill
#          HS   - Homeland Security
#          K    - Hurricane Katrina
#          IRM  - Information Resources Management
#          I    - Investigations
#          PL   - Public Liaison
#          ARRA - Recovery Act
#          RD   - Research and Development
#          RPP  - Risk and Program Performance
#          SR   - Special Reviews
#          L    - Superfund/Land
#          W    - Water
#          WTC  - World Trade Center
#          defaults to:
#            "E,I", reports in the Enforcement and Investigation topic areas.

ALL_TOPIC_AREAS = set(("A", "CB", "CC", "C", "CO", "X", "DWG", "EF", "E", "FM",
                       "FA", "G", "GU", "HS", "K", "IRM", "I", "PL", "ARRA",
                       "RD", "RPP", "SR", "L", "W", "WTC"))
BASE_URL = 'http://www.epa.gov/oig/reports.html'
RE_YEAR = re.compile(r'\d{4}')

def run(options):
  since = options.get('since')
  if since:
    since_dt = datetime.datetime.strptime(since, '%Y-%m-%d')
  else:
    since_dt = datetime.datetime.now() - datetime.timedelta(days=60)

  only = options.get('only')
  if only:
    only = set(only.split(','))
  else:
    only = set(('E', 'I'))

  index_body = utils.download(BASE_URL)

  current_year = None
  index = BeautifulSoup(index_body)
  tables = index.select('table.style1')
  for table in tables:
    trs = table.select('tr')
    for tr in trs:
      tds = tr.select('td')
      if len(tds) < 8:
        if len(tds) == 1:
          # Large column that indicates year
          col_links = tds[0].select('a')
          if len(col_links) == 1:
            col_text = col_links[0].text
            if RE_YEAR.match(col_text):
              current_year = col_text
        continue

      published_on_dt = datetime.datetime.strptime(tds[6].text, '%m/%d/%Y')
      if since_dt > published_on_dt:
        continue

      topic_areas = set(tds[7].text.split(', '))
      if not len(topic_areas.intersection(only)):
        continue

      report = report_from(tds, published_on_dt, current_year)
      inspector.save_report(report)


RE_PDF = re.compile('PDF', re.I)

def report_from(tds, published_on_dt, year):
  report = {
    'inspector': 'epa',
    'inspector_url': 'http://www.epa.gov/oig',
    'agency': 'epa',
    'agency_name': 'Environmental Protection Agency',
    'type': 'report',
    'year': year,
  }

  report_url = extract_url(tds[3])
  if not report_url:
    return None
  report_url = urljoin(BASE_URL, report_url)

  published_on = datetime.datetime.strftime(published_on_dt, '%Y-%m-%d')

  report_id = tds[0].text
  title = tds[1].text
  if not report_id:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  glance_url = extract_url(tds[2])
  if glance_url:
    glance_url = urljoin(BASE_URL, glance_url)

  if report_url[-4] == '.':
    file_type = report_url[-3:]
  else:
    file_type = '???'

  report.update({
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': published_on,
    # URL for 'At a glance' summary of the report
    'glance_url': glance_url,
    'file_type': file_type,
  })
  return report

def extract_url(td):
  url = None
  links = td.select('a')
  if len(links) == 1:
    url = links[0]['href']
  else:
    pdf_links = filter(lambda link: RE_PDF.search(link.text), links)
    if pdf_links:
      url = pdf_links[0]['href']
  return url

utils.run(run)
