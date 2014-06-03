#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from urllib.parse import urljoin, urlencode
import re
import os
import logging
from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.dodig.mil/pubs/index.cfm
# oldest year: 1986 (FY 1987)

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   report_id: limit to a particular report ID, skip others.
#
#   skip_downloaded: skip over any reports whose PDFs have been downloaded.
#      useful for resuming large fetches without making needless HTTP requests.
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
RE_PDF_BODY_MAYBE = re.compile('part ii$', re.I)
RE_PDF_HREF = re.compile(r'\.pdf\s*$')
RE_BACKUP_PDF_HREF = re.compile(r'Audit/reports', re.I)

RE_PDF_STATEMENT_TEXT = re.compile('here', re.I)
RE_PDF_STATEMENT_HREF = re.compile('statement', re.I)

RE_EXTERNALLY_HOSTED = re.compile('This file is hosted', re.I)
RE_RESCINDED = re.compile('This report was rescinded', re.I)
RE_UNUSED = re.compile('NUMBER NOT USED', re.I)

# more invasive/slow search for a link, needed when link has html inside,
# e.g. http://www.dodig.mil/programs/guam/index_detail.cfm?id=4933
def pdf_test(tag):
  is_link = (tag.name == 'a') and tag.has_attr('href')
  if not is_link: return False

  is_pdf = (RE_PDF_HREF.search(tag['href']) or RE_BACKUP_PDF_HREF.search(tag['href']))
  if not is_pdf: return False

  text = tag.text
  basic_match = (RE_PDF_CLICK_TEXT.search(text) or RE_PDF_LINK_TEXT.search(text) or RE_PDF_SARC_TEXT.search(text) or RE_PDF_BODY_MAYBE.search(text))
  if basic_match: return True

  # looser check - "here" is accepted, if it's also a statement
  simple_match = (RE_PDF_STATEMENT_TEXT.search(text) and RE_PDF_STATEMENT_HREF.search(tag['href']))
  if simple_match: return True

  return False

# any PDF
def any_pdf_test(tag):
  is_link = (tag.name == 'a') and tag.has_attr('href')
  if not is_link: return False

  is_pdf = (RE_PDF_HREF.search(tag['href']) or RE_BACKUP_PDF_HREF.search(tag['href']))
  return is_pdf

RE_OFFICIAL = re.compile('For Official Use Only', re.I)
RE_CLASSIFIED = re.compile('Classified', re.I)
RE_INTEL = re.compile('-INTEL-') # case-sensitive
RE_FOIA = re.compile('Freedom (?:of|on) Information Act', re.I)
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

  published_date = datetime.datetime.strptime(tds[0].text.strip(), '%m-%d-%Y')
  published_on = published_date.strftime('%Y-%m-%d')

  topic = tds[1].text

  report_id = tds[2].select('strong')
  if report_id:
    report_id = report_id[0].text.strip()
  else:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  # helper: use --report_id to skip all but that one
  only_id = options.get('report_id')
  if only_id and (only_id != report_id):
    return

  # helper: use --skip_downloaded to skip reports whose PDFs are on disk
  #   (drastically reduces calls to DOD landing pages)
  if options.get('skip_downloaded'):
    pdf_path = inspector.path_for({
      'report_id': report_id,
      'year': str(published_date.year),
      'inspector': 'dod'
    }, 'pdf')

    if os.path.exists("%s/%s" % (utils.data_dir(), pdf_path)):
      logging.warn("\tSkipping previously downloaded report, as asked.")
      return

  report_url, summary, maybe_unreleased, skip = fetch_from_landing_page(landing_url)

  if skip:
    return

  if (report_url is None) and maybe_unreleased:
    report['unreleased'] = True

  # giving up on any more Guam errors, we've caught as many cases
  # as we reasonably can, and there are Guam entries that aren't reports.
  elif (report_url is None) and (re.search("guam", landing_url)):
    return

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
  skip = False

  body = utils.download(landing_url)
  page = BeautifulSoup(body)

  report_tables = page.select('table[summary~="reports"]')
  # in the rare case that doesn't work, have faith
  if len(report_tables) == 0:
    report_tables = page.select('table')
  table = report_tables[0]
  examine_text = table.text

  maybe_unreleased = False
  if RE_OFFICIAL.search(examine_text) or RE_CLASSIFIED.search(examine_text) or RE_FOIA.search(examine_text) or RE_AFGHANISTAN.search(examine_text) or RE_RESTRICTED.search(examine_text) or RE_INTEL.search(examine_text):
    # 'Official use only' or 'Classified' materials don't have PDFs. Mark the
    # report metadata appropriately.
    maybe_unreleased = True

  # two varieties of normal report link
  link = page.find('a', text=RE_PDF_LINK_TEXT, href=RE_PDF_HREF)
  if not link:
    link = page.find('a', text=RE_PDF_CLICK_TEXT, href=RE_PDF_HREF)

  # Semi annual reports to Congress
  if not link:
    link = page.find('a', text=RE_PDF_SARC_TEXT, href=RE_PDF_HREF)

  # occurs for some multi-part reports, top/body/bottom
  if not link:
    link = page.find('a', text=RE_PDF_BODY_MAYBE, href=RE_PDF_HREF)

  # cases where .pdf is left off, ugh, e.g.
  # http://www.dodig.mil/pubs/report_summary.cfm?id=849
  if not link:
    link = page.find('a', text=RE_PDF_LINK_TEXT, href=RE_BACKUP_PDF_HREF)
    if link:
      add_pdf = True

  # last resort, slow python-based check for tightest requirements
  if not link:
    link = page.find(pdf_test)

  # before accepting *any* PDF, check for external links
  if not link and RE_EXTERNALLY_HOSTED.search(table.text):
    skip = True

  if not link and RE_RESCINDED.search(table.text):
    skip = True

  if not link and RE_UNUSED.search(table.text):
    skip = True

  # okay, I'll take *any* PDF
  if not link:
    link = table.find(any_pdf_test)

  href = link['href'].strip() if link else None
  if href and add_pdf:
    href = href + ".pdf"

  # some URLs have "/../" in the middle, and the redirects are trouble
  if href:
    href = href.replace("/../", "/")

  summary = None
  text_tr = page.select('tr[valign="top"] td')
  if text_tr:
    text = [node.strip() for node in text_tr[0].findAll(text=True)]
    summary = '\n\n'.join(text)
  if not summary:
    logging.info('\tno summary text found')

  return (href, summary, maybe_unreleased, skip)

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
