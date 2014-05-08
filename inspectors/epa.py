#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
from urlparse import urljoin
import re
from bs4 import BeautifulSoup
from utils import utils, inspector

#
# options:
#   since - year (YYYY) to fetch reports since.
#   year  - year (YYYY) to fetch reports from.
#
#   if neither `since` nor `year` is provided,
#     defaults to current year.
#
#   only - limit reports fetched to one or more topic area, comma-separated.
#          e.g. "EF,IRM".
#   defaults to "E,I" (Enforcement, Investigation)
#
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


ALL_TOPIC_AREAS = set(("A", "CB", "CC", "C", "CO", "X", "DWG", "EF", "E", "FM",
                       "FA", "G", "GU", "HS", "K", "IRM", "I", "PL", "ARRA",
                       "RD", "RPP", "SR", "L", "W", "WTC"))
BASE_URL = 'http://www.epa.gov/oig/reports.html'
RE_YEAR = re.compile(r'\d{4}')

def run(options):
  this_year = datetime.datetime.now().year

  since = options.get('since', None)
  if since:
    since = int(since)
    if since > this_year:
      since = this_year

  year = options.get('year', None)
  if year:
    year = int(year)
    if year > this_year:
      year = this_year

  if since:
    year_range = range(since, this_year + 1)
  elif year:
    year_range = range(year, year + 1)
  else:
    year_range = range(this_year, this_year + 1)


  only = options.get('only')
  if only:
    only = set(only.split(','))
  else:
    only = ALL_TOPIC_AREAS

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
      if published_on_dt.year not in year_range:
        continue

      topic_areas = set(tds[7].text.split(', '))
      if not len(topic_areas.intersection(only)):
        continue

      report = report_from(tds, published_on_dt, current_year)
      if report:
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
    'summary_only': False
  }

  report_id = tds[0].text

  report_url = extract_url(tds[3])
  if report_url:
    report_url = urljoin(BASE_URL, report_url)

  glance_url = extract_url(tds[2])
  if glance_url:
    glance_url = urljoin(BASE_URL, glance_url)

  # some reports only have the At A Glance summary,
  # e.g. when the full report is technical/sensitive
  if report_url is None and glance_url is not None:
    report_url = glance_url
    report['summary_only'] = True

  elif not report_url and not glance_url:
    raise Exception("Couldn't find a link for report %s" % report_id)

  published_on = datetime.datetime.strftime(published_on_dt, '%Y-%m-%d')

  title = tds[1].text.strip()
  if not report_id:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

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
