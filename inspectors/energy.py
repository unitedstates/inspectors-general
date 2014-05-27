#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from urllib.parse import urljoin, urlencode
import re
import logging
from bs4 import BeautifulSoup
from utils import utils, inspector

# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topcis, comma-separated, which
#            correspond to the topics defined on the site. For example: 'E,EC'.
#            Defaults to all topics.
#            Topic codes are:
#            E    - Energy
#            EC   - Environmental Cleanup
#            FA   - Financial Assistance
#            HR   - Human Resources
#            MA   - Management & Administration
#            NSS  - National Security & Safety
#            SI   - Science & Innovation
#
#   type - target the specific types for downloading reports, comma-separated.
#          These corresponds to the links in the left hand side of the report
#          site, such as "Calendar Year Reports" or "DOE Directives". This can
#          be specified along with --topics and the union of the two will be
#          fetched.
#          Type codes are:
#          RA   - American Recovery and Reinvestment Act
#          PR   - Peer Reviews
#          DOED - Department of Energy Directives
#          P    - Performance
#          SP   - Strategic Plan
#          T    - Testimony
#          FS   - Financial Statements
#          SR   - Semiannual Reports
#

BASE_URL = 'http://energy.gov/ig/calendar-year-reports'
TOPIC_TO_URL = {
  'E': 'http://energy.gov/ig/listings/energy-reports',
  'EC': 'http://energy.gov/ig/listings/environmental-cleanup-reports',
  'FA': 'http://energy.gov/ig/listings/financial-assistance-reports',
  'HR': 'http://energy.gov/ig/listings/human-resources-reports',
  'MA': 'http://energy.gov/ig/listings/management-administration-reports',
  'NSS': 'http://energy.gov/ig/listings/national-security-safety-reports',
  'SI': 'http://energy.gov/ig/listings/science-innovation-reports',
}

TYPE_TO_URL = {
  'RA': 'http://energy.gov/ig/listings/recovery-act-reports',
  'PR': 'http://energy.gov/ig/calendar-year-reports/peer-reviews',
  'DOED': 'http://energy.gov/ig/calendar-year-reports/doe-directives',
  'P': 'http://energy.gov/ig/calendar-year-reports/performance-plans',
  'SP': 'http://energy.gov/ig/calendar-year-reports/strategic-plans',
  'T': 'http://energy.gov/ig/listings/testimony-inspector-general',
  'FS': 'http://energy.gov/ig/listings/consolidated-financial-statements',
  'SR': 'http://energy.gov/ig/listings/semiannual-reports-congress',
  'WP': 'http://energy.gov/ig/calendar-year-reports/work-plans-manuals',
}

RE_CALENDAR_YEAR = re.compile(r'Calendar Year (\d{4})')
RE_REPORT_ID = re.compile('(.+): (.+)')
RE_NOT_AVAILABLE = re.compile('not available for viewing', re.I)
RE_CLASSIFIED = re.compile('report is classified', re.I)

def run(options):
  for url in urls_for(options):
    page = BeautifulSoup(utils.download(url))

    for node in page.select('.node'):
      report = report_from(node)
      if report:
        inspector.save_report(report)

def report_from(node):
  report = {
    'inspector': 'energy',
    'inspector_url': 'http://energy.gov/ig/office-inspector-general',
    'agency': 'energy',
    'agency_name': 'Department of Energy',
  }

  date = node.select('.date')[0]
  published_on = datetime.datetime.strptime(date.text, '%B %d, %Y')
  published_on = published_on.strftime('%Y-%m-%d')

  title_p = node.select('.field-item p')[0]
  title = title_p.text.strip()

  title_link = node.select('.title-link')[0]
  landing_url = urljoin(BASE_URL, title_link['href'])

  title_link_span = title_link.select('span')[0]
  md = RE_REPORT_ID.search(title_link_span.text)
  if md:
    sub_type = md.group(1).strip().replace(' ', '_').lower()
    report_id = md.group(2).strip().replace('/', '-')
  else:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  report_url, summary, unreleased = fetch_from_landing_page(landing_url)

  if unreleased:
    report['unreleased'] = True

  report.update({
    'report_id': report_id,
    'type': 'report',
    'sub_type': sub_type,
    'url': report_url,
    'landing_url': landing_url,
    'summary': summary,
    'title': title,
    'published_on': published_on
  })
  return report
  
def fetch_from_landing_page(landing_url):
  """Returns a tuple of (pdf_link, summary_text, is_unreleased)."""
  unreleased = False
  page = BeautifulSoup(utils.download(landing_url))

  summary = None
  field_items = page.select('.field-items')
  if field_items:
    text = [node.strip() for node in field_items[0].findAll(text=True)]
    summary = '\n\n'.join(text)
  if not summary:
    logging.info('\tno summary text found')

  if (summary and (RE_NOT_AVAILABLE.search(summary)
                   or RE_CLASSIFIED.search(summary))):
    unreleased = True

  report_url = None
  pdf_link = page.select('.file a')
  if not pdf_link:
    logging.warn('No pdf link found on page: {0}'.format(landing_url))
  else:
    report_url = pdf_link[0]['href']

  return report_url, summary, unreleased

def urls_for(options):
  type_ = options.get('type')
  if type_:
    # TODO: Do something with types
    pass

  only = options.get('topics')
  if only:
    only = set(only.split(','))
    yield from urls_for_topics(options, only)
    return

  # Not getting reports from specific topics, iterate over all Calendar Year
  # reports.
  year_range = inspector.year_range(options)
  url = BASE_URL

  page = BeautifulSoup(utils.download(url))

  # Iterate over each "Calendar Year XXXX" link
  for li in page.select('.field-items li'):
    md = RE_CALENDAR_YEAR.search(li.text)
    if md:
      cur_year = int(md.group(1))
      if cur_year >= year_range[0] and cur_year <= year_range[-1]:
        href = li.select('a')[0]['href']
        next_url = urljoin(url, href)
        # The first page of reports is yielded.
        yield next_url

        # Next, read all the pagination links for the page and yield those. So
        # far, I haven't seen a page that doesn't have all of the following
        # pages enumerated.
        next_page = BeautifulSoup(utils.download(next_url))
        for link in next_page.select('li.pager-item a'):
          yield urljoin(url, link['href'])

def urls_for_topics(options, only):
  year_range = inspector.year_range(options)
  first_date = datetime.datetime(year_range[0], 1, 1)

  for topic in only:
    url = TOPIC_TO_URL[topic]
    yield url

    page = BeautifulSoup(utils.download(url))

    is_last_page = False
    for date in page.select('.date'):
      cur_date = datetime.datetime.strptime(date.text.strip(), '%B %d, %Y')
      if cur_date < first_date:
        is_last_page = True
        break
    if is_last_page:
      continue
    
    for link in page.select('li.pager-item a'):
      yield urljoin(url, link['href'])


utils.run(run) if (__name__ == "__main__") else None
