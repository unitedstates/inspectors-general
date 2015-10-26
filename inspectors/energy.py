#!/usr/bin/env python

import datetime
from urllib.parse import urljoin
import re
import logging
from utils import utils, inspector

# website: http://energy.gov/ig/
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#
#   report_id - limit to a particular report
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
#            RA   - American Recovery and Reinvestment Act
#            PR   - Peer Reviews
#            DOED - Department of Energy Directives
#            P    - Performance
#            SP   - Strategic Plan
#            T    - Testimony
#            FS   - Financial Statements
#            SR   - Semiannual Reports
#

# blacklist of broken report pages -
# these are being sent to the IG's office for their fixing,
# so they can be taken off the blacklist.
BROKEN_IDS = ('OAS-L-04-08')

# Landing pages to skip -- these are duplicates of other landing pages
DUPLICATE_LANDING_PAGES = (
  'http://energy.gov/ig/downloads/audit-report-oas-l-11-02-0',
  'http://energy.gov/ig/downloads/special-inquiry-oas-sr-10-04',
  'http://energy.gov/ig/downloads/inpsection-report-ig-0671',
  'http://energy.gov/ig/downloads/inspection-report-ig-0633',
  'http://energy.gov/ig/downloads/inspection-report-ins-o-98-02-0',
)

BASE_URL = 'http://energy.gov/ig/calendar-year-reports'
TOPIC_TO_URL = {
  'E': 'http://energy.gov/ig/listings/energy-reports',
  'EC': 'http://energy.gov/ig/listings/environmental-cleanup-reports',
  'FA': 'http://energy.gov/ig/listings/financial-assistance-reports',
  'HR': 'http://energy.gov/ig/listings/human-resources-reports',
  'MA': 'http://energy.gov/ig/listings/management-administration-reports',
  'NSS': 'http://energy.gov/ig/listings/national-security-safety-reports',
  'SI': 'http://energy.gov/ig/listings/science-innovation-reports',
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

# Reports in these topics are not listed in the normal "Calendar Year" reports.
# When we get no specification for topics, we will scrape all of the relevant
# Calendar Year pages, as well as the pages for these topics in order to be
# comprehensive.
# These are tuples of the topic code and the report_type that should be used
# when scraping reports of that topic
ADDITIONAL_TOPICS= [
  ('PR', 'peer_review'),
  ('DOED', 'doe_directive'),
  ('P', 'performance_plan'),
  ('SP', 'strategic_plan'),
  ('T', 'testimony'),
  ('SR', 'semiannual_report'),
]
TOPIC_TO_REPORT_TYPE = dict(ADDITIONAL_TOPICS)

RE_CALENDAR_YEAR = re.compile(r'Calendar Year (\d{4})')
RE_REPORT_ID = re.compile('(.+): (\S+[-/]\S+)')
RE_NOT_AVAILABLE = re.compile('not available (?:for|of) viewing', re.I)
RE_NOT_AVAILABLE_2 = re.compile('not publically available', re.I)
RE_NOT_AVAILABLE_3 = re.compile('official use only', re.I)
RE_NOT_AVAILABLE_4 = re.compile('to obtain a copy of this report please email', re.I)
RE_WITHDRAWN = re.compile('report is temporarily unavailable', re.I)
RE_CLASSIFIED = re.compile('report is classified', re.I)

class EnergyScraper(object):
  def run(self, options):
    self.options = options
    self.year_range = inspector.year_range(self.options, archive)
    self.first_date = datetime.datetime(self.year_range[0], 1, 1)
    self.last_date = datetime.datetime(self.year_range[-1], 12, 31)

    for url in self.urls_for():
      page = utils.beautifulsoup_from_url(url)

      nodes = page.select('.energy-listing__results .node')
      if not nodes:
        nodes = page.select('.field-items .node')
      if not nodes:
        nodes = page.select('.node')
      if not nodes:
        raise inspector.NoReportsFoundError("Department of Energy (%s)" % url)

      for node in nodes:
        report = self.report_from(node)
        if report:
          inspector.save_report(report)
        else:
          # Empty report indicates a report out of the date range, or not the ID.
          continue

  def report_from(self, node):
    report = {
      'inspector': 'energy',
      'inspector_url': 'http://energy.gov/ig/office-inspector-general',
      'agency': 'energy',
      'agency_name': 'Department of Energy',
    }

    date = node.select('.date')[0]
    published_on = datetime.datetime.strptime(date.text, '%B %d, %Y')
    if published_on < self.first_date or published_on > self.last_date:
      # Out of date range, skip this one.
      return
    published_on = published_on.strftime('%Y-%m-%d')

    title_p = node.select('.field-item p')[0]
    title = title_p.text.strip()

    title_link = node.select('.title-link')[0]
    landing_url = urljoin(BASE_URL, title_link['href'])

    title_link_span = title_link.select('span')[0]
    md = RE_REPORT_ID.search(title_link_span.text)
    if md:
      report['sub_type'] = md.group(1).strip().replace(' ', '_').lower()
      report_id = md.group(2).strip().replace('/', '-')
    else:
      title_slug = re.sub(r'\W', '', title[:16])
      report_id = (published_on + '-' + title_slug)

    # Some reports are just broken. Move on, but they are
    # noted here and should be reported to the IG.
    if report_id in BROKEN_IDS:
      logging.warn("[%s] Skipping, broken report." % report_id)
      return

    # Some reports have been uploaded twice, and have two landing pages.
    if landing_url in DUPLICATE_LANDING_PAGES:
      logging.warn("Skipping duplicate landing page %s" % landing_url)
      return

    # debugging: if we're limiting to a particular report,
    # and this isn't it, back out
    only_report_id = self.options.get('report_id')
    if only_report_id and (only_report_id != report_id):
      logging.warn("[%s] Skipping, not what was asked for." % report_id)
      return

    report_url, summary, unreleased = self.fetch_from_landing_page(landing_url)

    if landing_url == 'http://energy.gov/ig/downloads/audit-report-cr-b-97-04-0':
      # The metadata on this landing page is incorrect
      report_id = 'ER-B-97-04'
      title = 'Audit of Selected Hazardous Waste Remedial Actions Program Costs'
      summary = ''
      published_on = '1997-08-11'

    if unreleased:
      report['unreleased'] = True

    report.update({
      'report_id': report_id,
      'type': self.report_type if self.report_type else 'report',
      'url': report_url,
      'landing_url': landing_url,
      'summary': summary,
      'title': title,
      'published_on': published_on
    })
    return report

  def fetch_from_landing_page(self, landing_url):
    """Returns a tuple of (pdf_link, summary_text, is_unreleased)."""
    unreleased = False
    page = utils.beautifulsoup_from_url(landing_url)

    summary = None
    field_items = page.select('.field-items')
    if field_items:
      text = [node.strip() for node in field_items[0].findAll(text=True)]
      summary = '\n\n'.join(text).strip()
    if not summary:
      logging.info('\tno summary text found')

    # sanitize now instead of later, to compare to regexes
    else:
      summary = inspector.sanitize(summary)

    if (summary and (RE_NOT_AVAILABLE.search(summary)
                     or RE_NOT_AVAILABLE_2.search(summary)
                     or RE_NOT_AVAILABLE_3.search(summary)
                     or RE_NOT_AVAILABLE_4.search(summary)
                     or RE_WITHDRAWN.search(summary)
                     or RE_CLASSIFIED.search(summary))):
      unreleased = True

    report_url = None
    pdf_link = page.select('.file a')
    if not pdf_link:
      logging.warn('No pdf link found on page: {0}'.format(landing_url))
    else:
      report_url = pdf_link[0]['href']

    return report_url, summary, unreleased

  def urls_for(self):
    only = self.options.get('topics')
    if only: # if only...
      only = set(only.split(','))
      only = [(o, TOPIC_TO_REPORT_TYPE[o]) if o in TOPIC_TO_REPORT_TYPE else o
              for o in only]
      yield from self.urls_for_topics(only)
      # If there are topics selected, ONLY yield URLs for those.
      return

    # First yield the URLs for the topics that are tangential to the main
    # Calendar Year reports.
    yield from self.urls_for_topics(ADDITIONAL_TOPICS)

    # Not getting reports from specific topics, iterate over all Calendar Year
    # reports.
    page = utils.beautifulsoup_from_url(BASE_URL)

    # Iterate over each "Calendar Year XXXX" link
    for li in page.select('.field-items li'):
      md = RE_CALENDAR_YEAR.search(li.text)
      if md:
        cur_year = int(md.group(1))
        if cur_year >= self.year_range[0] and cur_year <= self.year_range[-1]:
          href = li.select('a')[0]['href']
          next_url = urljoin(BASE_URL, href)
          # The first page of reports is yielded.
          yield next_url

          # Next, read all the pagination links for the page and yield those. So
          # far, I haven't seen a page that doesn't have all of the following
          # pages enumerated.
          next_page = utils.beautifulsoup_from_url(next_url)
          for link in next_page.select('li.pager-item a'):
            yield urljoin(BASE_URL, link['href'])


  def urls_for_topics(self, topics):
    for topic in topics:
      # Topic might be a tuple for ADDITIONAL_TOPICS (not ones from command
      # line).
      self.report_type = None
      if isinstance(topic, tuple):
        topic, report_type = topic
        self.report_type = report_type

      last_page = False

      url = TOPIC_TO_URL[topic]
      page = utils.beautifulsoup_from_url(url)
      page_started = self.is_first_page(page)
      if page_started:
        yield url

      for link in page.select('li.pager-item a'):
        next_url = urljoin(url, link['href'])
        next_page = utils.beautifulsoup_from_url(next_url)
        if not page_started:
          page_started = self.is_first_page(next_page)
        if page_started:
          yield next_url
        last_page = self.is_last_page(next_page)
        if last_page:
          break
      if last_page:
        continue
    self.report_type = None  # Clear this out afterwards

  def is_first_page(self, page):
    for date in page.select('.date'):
      cur_date = datetime.datetime.strptime(date.text.strip(), '%B %d, %Y')
      if cur_date <= self.last_date:
        return True
    return False

  def is_last_page(self, page):
    for date in page.select('.date'):
      cur_date = datetime.datetime.strptime(date.text.strip(), '%B %d, %Y')
      if cur_date < self.first_date:
        return True
    return False

def run(options):
  EnergyScraper().run(options)

utils.run(run) if (__name__ == "__main__") else None
