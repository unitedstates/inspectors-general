#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from urllib.parse import urljoin, urlencode
import re
import logging
from bs4 import BeautifulSoup
from utils import utils, inspector

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   office - limit reports fetched to one or more office, comma-separated.
#           e.g. "IE,ISPA". These are the offices/"components" defined by the
#           site.
#   defaults to "A" (Audit)
#
#          office codes are:
#          A    - Audit
#          IE   - Inspections & Evaluations
#          ISPA - Intelligence & Special Program Assessments
#          APO  - P&O - Audit Policy & Oversight
#          IPO  - P&O - Investigative Policy & Oversight
#          TA   - P&O - Technical Assessment
#          SPO  - Special Plans & Operations
#          O    - Others

OFFICES = {
  'A': 'Audit',
  'IE': 'Inspections and Evaluations',
  'ISPA': 'Intelligence and Special Program Assessments',
  'APO': 'Audit Policy and Oversight',
  'IPO': 'Investigative Policy and Oversight',
  'TA': 'Technical Assessment',
  'SPO': 'Special Plans and Operations',
  'O': 'Others',
}
BASE_URL = 'http://www.dodig.mil/pubs/index.cfm'

RE_DIGITS = re.compile(r'^\d+$')

RE_PDF_LINK_TEXT = re.compile('Complete PDF')
RE_PDF_CLICK_TEXT = re.compile('click here', re.I)
RE_PDF_HREF = re.compile(r'\.pdf$')

RE_OFFICIAL = re.compile('For Official Use Only')
RE_CLASSIFIED = re.compile('Classified')
RE_NO_DATA = re.compile('No Data')

def run(options):
  only = options.get('topics')
  if only:
    only = set(only.split(','))
  else:
    # Default to Audit
    only = ['A']

  for url in urls_for(options, only):
    body = utils.download(url)
    page = BeautifulSoup(body)

    report_table = page.select('table[summary~="reports"]')[0]
    for tr in report_table.select('tr')[1:]:
      tds = tr.select('td')
      if len(tds) == 1:
        # Page has no reports, simply a "No Data" indication for these dates.
        break
      report = report_from(tds)
      if report:
        inspector.save_report(report)

def report_from(tds):
  report = {
    'inspector': 'dod',
    'inspector_url': 'http://www.dodig.mil/',
    'agency': 'dod',
    'agency_name': 'Department of Defense',
  }

  title_link = tds[2].select('a')[0]
  title = title_link.text.strip().replace('\r\n', ' ')
  landing_url = urljoin(BASE_URL, title_link['href'])
  if RE_OFFICIAL.search(tds[2].text) or RE_CLASSIFIED.search(tds[2].text):
    # 'Official use only' or 'Classified' materials don't have PDFs. Mark the
    # report metadata appropriately.
    report['unreleased'] = True

  published_on = datetime.datetime.strptime(tds[0].text.strip(), '%m-%d-%Y')
  published_on = published_on.strftime('%Y-%m-%d')

  topic = tds[1].text

  report_id = tds[2].select('strong')
  if report_id:
    report_id = report_id[0].text.strip()
  else:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  report_url, summary = fetch_from_landing_page(landing_url)
  if report.get('unreleased'):
    report_url = None

  office = tds[3].text.strip()

  report.update({
    'report_id': report_id,
    'url': report_url,
    'landing_url': landing_url,
    'summary': summary,
    'title': title,
    'topic': topic,
    'office': office,
    'published_on': published_on
  })
  return report

def fetch_from_landing_page(landing_url):
  """Returns a tuple of (pdf_link, summary_text)."""
  body = utils.download(landing_url)
  page = BeautifulSoup(body)
  link = page.find('a', text=RE_PDF_LINK_TEXT, href=RE_PDF_HREF)
  if not link:
    link = page.find('a', text=RE_PDF_CLICK_TEXT, href=RE_PDF_HREF)
  href = link['href'] if link else None
  
  summary = None
  text_tr = page.select('tr[valign="top"] td')
  if text_tr:
    text = [node.strip() for node in text_tr[0].findAll(text=True)]
    summary = '\n\n'.join(text)
  if not summary:
    logging.info('\tno summary text found')

  return (href, summary)

def urls_for(options, only):
  year_range = inspector.year_range(options)
  for office in only:
    # there's always a first year, and it defaults to current year
    params = {}
    params['searchdate1'] = '01/01/%s' % year_range[0]
    params['searchdate2'] = '12/31/%s' % year_range[-1] # could be the same year
    params['office'] = OFFICES[office]
    params['sort'] = 'report_number'
    params['order'] = 'desc'

    query_string = urlencode(params)
    url = '{0}?{1}'.format(BASE_URL, query_string)
    yield url

    body = utils.download(url)
    page = BeautifulSoup(body)

    # Find the pagination links on the page and yield them all
    for link in page.select('a'):
      if link['href'].startswith('?') and RE_DIGITS.match(link.text):
        yield BASE_URL + link['href']

utils.run(run) if (__name__ == "__main__") else None
