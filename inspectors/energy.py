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
#   category - target a specific category for downloading reports. This
#              corresponds to the categories in the left hand side of the report
#              site, such as "Calendar Year Reports" or "DOE Directives".
#              Only one category code may be specified. NOTE: You cannot specify
#              both "--topics==" and "--category=" arguments to the scraper.
#              Only the --category directive will be used.
#              Category codes are:
#              CY  - Calendary Year Reports
#

TOPIC_TO_URL = {
  'E': 'http://energy.gov/ig/listings/energy-reports',
  'EC': 'http://energy.gov/ig/listings/environmental-cleanup-reports',
  'FA': 'http://energy.gov/ig/listings/financial-assistance-reports',
  'HR': 'http://energy.gov/ig/listings/human-resources-reports',
  'MA': 'http://energy.gov/ig/listings/management-administration-reports',
  'NSS': 'http://energy.gov/ig/listings/national-security-safety-reports',
  'SI': 'http://energy.gov/ig/listings/science-innovation-reports',
}

CATEGORY_TO_URL = {
  'CY': 'http://energy.gov/ig/calendar-year-reports',
}

RE_CALENDAR_YEAR = re.compile(r'Calendar Year (\d{4})')

def run(options):
  for url in urls_for(options):
    print(url)

  if False:
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

def urls_for(options):
  only = options.get('topics')
  if only:
    only = set(only.split(','))
    yield from urls_for_topics(options, only)
    return

  # Not getting reports from specific topics, iterate over all Calendar Year
  # reports.
  year_range = inspector.year_range(options)
  url = CATEGORY_TO_URL['CY']

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
    
def pagination_links_for_year(url):
  page = BeautifulSoup(utils.download(url))

  

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
