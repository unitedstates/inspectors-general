#!/usr/bin/env python

import datetime
from urllib.parse import urljoin
import re
import os.path
from bs4 import BeautifulSoup
from utils import utils, inspector

archive = 1996

# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topic area, comma-separated.
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
  year_range = inspector.year_range(options, archive)

  only = options.get('topics')
  if only:
    only = set(only.split(','))
  else:
    only = ALL_TOPIC_AREAS

  index_body = utils.download(BASE_URL)

  current_year = None
  index = BeautifulSoup(index_body, "lxml")
  tables = index.select('table.style1')
  if not tables:
    raise inspector.NoReportsFoundException("EPA")
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
    'summary_only': False
  }

  report_url = extract_url(tds[3])
  if report_url:
    report_url = urljoin(BASE_URL, report_url)

  if report_url == "http://www.nsf.gov/oig/USMFS05.pdf":
    report_url = "https://www.nsf.gov/oig/_pdf/USMFS05.pdf"

  glance_url = extract_url(tds[2])
  if glance_url:
    glance_url = urljoin(BASE_URL, glance_url)

  # some reports only have the At A Glance summary,
  # e.g. when the full report is technical/sensitive
  if report_url is None and glance_url is not None:
    report_url = glance_url
    report['summary_only'] = True

  elif not report_url and not glance_url:
    raise Exception("Couldn't find a link for report!")


  report_id = re.sub("\s+", " ", tds[0].text).strip()
  # fallback, only needed for one testimony, apparently
  if (report_id == "") or (not report_id):
    report_id, extension = os.path.splitext(report_url.split("/")[-1])

  published_on = datetime.datetime.strftime(published_on_dt, '%Y-%m-%d')

  # Don't take all the text because it can sometimes include a <br> and some
  # annotation.
  title = tds[1].contents[0].strip()
  if not report_id:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  # Report 2002-M-000013 is listed twice, as it includes multiple documents
  if title.find("Logic Models Diagrams") != -1:
    report_id = report_id + "-logic-models-diagrams"

  report.update({
    'report_id': report_id,
    'url': report_url,
    # URL for 'At a glance' summary of the report
    'summary_url': glance_url,
    'title': title,
    'published_on': published_on
  })
  return report

def extract_url(td):
  url = None
  links = td.select('a')
  if len(links) == 1:
    url = links[0]['href']
  else:
    pdf_links = [link for link in links if RE_PDF.search(link.text)]
    if pdf_links:
      url = pdf_links[0]['href']
  return url

utils.run(run) if (__name__ == "__main__") else None
