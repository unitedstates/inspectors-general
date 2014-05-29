#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from urllib.parse import urljoin, urlencode
import re
import logging
from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.dodig.mil/pubs/index.cfm
# Oldest report: FY 1987

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   report_id: limit to a particular report ID, skip others.
#
#   topics - limit reports fetched to one or more office, comma-separated.
#            e.g. "IE,ISPA". These are the offices/"components" defined by the
#            site. Defaults to all offices. (NOTE: this parameter is named
#            'topics' to line up better with other IG scrapers.)
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
RE_NEXT_10 = re.compile('Next 10 Pages')

RE_PDF_LINK_TEXT = re.compile('Complete PDF')
RE_PDF_CLICK_TEXT = re.compile('click here', re.I)
RE_PDF_SARC_TEXT = re.compile('semiannual report', re.I)
RE_PDF_HREF = re.compile(r'\.pdf\s*$')
RE_BACKUP_PDF_HREF = re.compile(r'Audit/reports', re.I)

RE_OFFICIAL = re.compile('For Official Use Only', re.I)
RE_CLASSIFIED = re.compile('Classified', re.I)
RE_FOIA = re.compile('Freedom of Information Act', re.I)
RE_RESTRICTED = re.compile('Restricted', re.I)
RE_AFGHANISTAN = re.compile('Provided to the Security Forces of Afghanistan', re.I)

def run(options):
  only = options.get('topics')
  if only:
    only = set(only.split(','))
  else:
    # Default to all offices, whee!
    only = list(OFFICES.keys())

  for url in urls_for(options, only):
    body = utils.download(url)
    page = BeautifulSoup(body)

    report_table = page.select('table[summary~="reports"]')[0]
    for tr in report_table.select('tr')[1:]:
      tds = tr.select('td')
      if len(tds) == 1:
        # Page has no reports, simply a "No Data" indication for these dates.
        break
      report = report_from(tds, options)
      if report:
        inspector.save_report(report)

def report_from(tds, options):
  report = {
    'inspector': 'dod',
    'inspector_url': 'http://www.dodig.mil/',
    'agency': 'dod',
    'agency_name': 'Department of Defense',
  }

  title_link = tds[2].select('a')[0]
  title = title_link.text.strip().replace('\r\n', ' ')
  landing_url = urljoin(BASE_URL, title_link['href'])
  maybe_unreleased = False
  if RE_OFFICIAL.search(tds[2].text) or RE_CLASSIFIED.search(tds[2].text) or RE_FOIA.search(tds[2].text) or RE_AFGHANISTAN.search(tds[2].text) or RE_RESTRICTED.search(tds[2].text):
    # 'Official use only' or 'Classified' materials don't have PDFs. Mark the
    # report metadata appropriately.
    maybe_unreleased = True

  published_on = datetime.datetime.strptime(tds[0].text.strip(), '%m-%d-%Y')
  published_on = published_on.strftime('%Y-%m-%d')

  topic = tds[1].text

  report_id = tds[2].select('strong')
  if report_id:
    report_id = report_id[0].text.strip()
  else:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  # helper: if we asked for just one report ID, skip the rest
  only_id = options.get('report_id')
  if only_id and (only_id != report_id):
    return

  report_url, summary = fetch_from_landing_page(landing_url)

  if (report_url is None) and maybe_unreleased:
    report['unreleased'] = True

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
  add_pdf = False

  body = utils.download(landing_url)
  page = BeautifulSoup(body)
  link = page.find('a', text=RE_PDF_LINK_TEXT, href=RE_PDF_HREF)
  if not link:
    link = page.find('a', text=RE_PDF_CLICK_TEXT, href=RE_PDF_HREF)
  if not link:
    link = page.find('a', text=RE_PDF_SARC_TEXT, href=RE_PDF_HREF)

  # cases where .pdf is left off, ugh, e.g.
  # http://www.dodig.mil/pubs/report_summary.cfm?id=849
  if not link:
    link = page.find('a', text=RE_PDF_LINK_TEXT, href=RE_BACKUP_PDF_HREF)
    add_pdf = True


  href = link['href'].strip() if link else None
  if href and add_pdf:
    href = href + ".pdf"

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

    for url in get_pagination_urls(page):
      yield url

def get_pagination_urls(page):
  """Find the pagination links on the page and yield them all.

  This method recursively downloads new pages in the case that there are more
  than 10.
  """
  for link in page.select('a'):
    if link['href'].startswith('?') and RE_DIGITS.match(link.text):
      yield BASE_URL + link['href']
    elif link['href'].startswith('/pubs') and RE_NEXT_10.search(link.text):
      new_url = urljoin(BASE_URL, link['href'])
      page = BeautifulSoup(utils.download(new_url))
      for link in get_pagination_urls(page):
        yield link


utils.run(run) if (__name__ == "__main__") else None
