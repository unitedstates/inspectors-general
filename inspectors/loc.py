#!/usr/bin/env python

import datetime
import logging
from urllib.parse import urljoin
import re

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www.loc.gov/about/office-of-the-inspector-general/
archive = 2001

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_BY_YEAR_URL = 'https://www.loc.gov/about/office-of-the-inspector-general/annual-reports/'
REPORTS_TESTIMONY_URL = 'https://www.loc.gov/about/office-of-the-inspector-general/congressional-testimony/'
REPORTS_PEER_REVIEWS_URL = 'https://www.loc.gov/about/office-of-the-inspector-general/peer-reviews/'

OTHER_REPORTS = {
  'http://lcweb2.loc.gov/master/libn/about/office-of-the-inspector-general/documents/LCR211-6-oct2010.pdf': '2010-10-01'
}

REPORT_ID_TO_EST_DATE = {
  'TLHAOTBMPIAMECT': datetime.datetime(2013, 3, 1),
  'WTTSOTGPARMA': datetime.datetime(2013, 3, 1),
  'MDCITSOICBISCFPR': datetime.datetime(2010, 10, 1),
  'RRSASBRJ2T2A': datetime.datetime(2007, 7, 1),
}

PARTS_MONTH = ('(January|February|March|April|May|June|July|August|September|'
               'October|November|December)')
RE_PUBLIC_RELEASE = re.compile('Not for Public Release', re.I)
RE_DATE = re.compile(r'%s +\d\d\d\d' % PARTS_MONTH)
RE_SHORT_DATE = re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Oct|Nov|Dec)'
                           r' +\d\d\d\d')
RE_LONG_DATE = re.compile(r'%s \d\d,? +\d\d\d\d' % PARTS_MONTH)
RE_FISCAL_YEAR = re.compile('Fiscal Year (\d\d\d\d)')
RE_OWLC = re.compile('Open +World +Leadership +Center')
RE_JMCF = re.compile('James +Madison +Council +Fund')

def generate_id(title, published_on=None):
  """Generates a report id given the report title and published date.

  This generally tries to be clever and uses the first letter of each name of
  the title, then the month date and year of the report as the ID.
  """
  words = title.split()
  letters = [word[0] for word in words if re.match(r'\w', word[0])]
  slug = ''.join(letters).upper()
  if published_on:
    return '%s-%s' % (slug[:16], published_on.strftime('%Y-%m-%d'))
  else:
    return slug


class LibraryOfCongressScraper(object):
  def __init__(self, options):
    self.options = options
    self.year_range = inspector.year_range(options, archive)

  def run(self):
    self.get_reports_by_year()

    # Get congressional testimony.
    self.get_listed_reports(REPORTS_TESTIMONY_URL)

    # Get peer reviews.
    self.get_listed_reports(REPORTS_PEER_REVIEWS_URL)

  def get_reports_by_year(self):
    # This page contains semianual reports as well as a few Audit reports for
    # Fiscal Year 2014 and links to sub-pages that contain links for other
    # fiscal years.
    doc = BeautifulSoup(utils.download(REPORTS_BY_YEAR_URL))

    # Get the semiannual reports to Congress.
    self.get_semiannual_reports_to_congress(doc)

    # Reports that are 'bare' on the page, listed explicitly
    bare_report_ul, link_subpage_ul = self.get_uls_past_audit_header(doc)
    self.get_bare_reports(bare_report_ul)

    # Links on the page to audit reports from past fiscal years
    for li in link_subpage_ul.find_all('li'):
      link = li.find('a')
      if link:
        next_url = urljoin(REPORTS_BY_YEAR_URL, link['href'])
        doc = BeautifulSoup(utils.download(next_url))
        uls = self.get_uls_past_audit_header(doc)
        assert len(uls) == 1, ('Mysterious additional ul data on page: %s' %
                               next_url)
        self.get_bare_reports(uls[0])

  def get_listed_reports(self, url):
    doc = BeautifulSoup(utils.download(url))
    article = doc.select('.article')[0]
    results = article.find_all('ul')
    if not results:
      raise inspector.NoReportsFoundError("Library of Congress (%s)" % url)
    for ul in results:
      self.get_bare_reports(ul)

  def get_semiannual_reports_to_congress(self, doc):
    header = doc.find_all(text=re.compile('Semiannual Reports'))
    ul = header[0].parent.find_next_sibling()
    results = ul.find_all('li')
    if not results:
      raise inspector.NoReportsFoundError("Library of Congress (semiannual reports)")
    for li in results:
      link = li.find('a')
      report_url = urljoin(REPORTS_BY_YEAR_URL, link['href'])
      report_id = report_url.split('/')[-1].split('.')[0]
      title = 'Semiannual Report to the Congress: %s' % link.text.strip()
      published_on = datetime.datetime.strptime(link.text.strip(), '%B %Y')
      report = self.report_from(report_id, report_url, title, published_on)
      if report:
        inspector.save_report(report)

  def get_bare_reports(self, bare_report_ul):
    for li in bare_report_ul.find_all('li'):
      link = li.find('a')
      report_url = None
      unreleased = False
      if link:
        report_url = urljoin(REPORTS_BY_YEAR_URL, link['href'])
        text = link.text
      elif li.find_all(text=RE_PUBLIC_RELEASE):
        unreleased = True
        text = li.get_text()
      else:
        unreleased = True
        text = li.get_text()
        # Annoying reports that aren't public (apparently) but not marked such.
        logging.warning('Found report with no PDF link but not marked "Not for '
                        'Public Release": %s', text)

      title = text.replace(' (Not for Public Release)', '')
      parts = [txt.strip() for txt in text.rsplit(',', 1)]
      if len(parts) == 1:
        published_on = self.date_from_string_or_die(text, report_url)
      else:
        _, published_text = parts
        if unreleased:
          published_text = published_text.replace(
            ' (Not for Public Release)', '')
        published_on = self.date_from_string_or_die(
          published_text, report_url, fallback=text)

      report_id = generate_id(title, published_on)
      report = self.report_from(report_id, report_url, title, published_on)
      if report:
        if unreleased:
          report['unreleased'] = True
          report['landing_url'] = REPORTS_BY_YEAR_URL

          # Check for duplicate and discard
          if report_id == "JMCFFY2FSM2-2009-03-01": continue

        inspector.save_report(report)

  def get_uls_past_audit_header(self, doc):
    # Yes there is mysteriously an extra space in the document before the word
    # 'Reports'.
    header = doc.find_all(text=re.compile('Audits and Other +Reports'))
    return header[0].parent.find_next_siblings('ul')

  def date_from_string_or_die(self, title, report_url, fallback=None):
    md = RE_DATE.search(title)
    if md:
      return datetime.datetime.strptime(md.group(0), '%B %Y')

    md = RE_SHORT_DATE.search(title)
    if md:
      # Seriously IG? Sept?
      return datetime.datetime.strptime(md.group(0).replace('Sept', 'Sep'),
                                        '%b %Y')

    md = RE_FISCAL_YEAR.search(title)
    if md:
      year = int(md.group(1))
      return datetime.datetime(year+1, 11, 1)

    md = RE_LONG_DATE.search(title)
    if md:
      if ',' in md.group(0):
        return datetime.datetime.strptime(md.group(0), '%B %d, %Y')
      else:
        return datetime.datetime.strptime(md.group(0), '%B %d %Y')

    # Ridiculous recursion to avoid exception handling in the top level.
    if fallback:
      try:
        return self.date_from_string_or_die(fallback, report_url)
      except ValueError:
        pass

    # If the string is not a title but instead a published_on_text, this will
    # definitely fail, but it's no big deal to try.
    temp_id = generate_id(title)
    if temp_id in REPORT_ID_TO_EST_DATE:
     return REPORT_ID_TO_EST_DATE[temp_id]

    raise ValueError('Found report with no listed and no hardcoded date:'
                     '%s <%s>' % (title, report_url))


  def report_from(self, report_id, report_url, title, published_on):
    if published_on.year not in self.year_range:
      logging.debug("[%s] Skipping, not in requested range." % report_url)
      return

    agency = 'loc'
    agency_name = 'Library of Congress'
    if RE_OWLC.search(title):
      agency = 'owlc'
      agency_name = 'Open World Leadership Center'
    elif RE_JMCF.search(title):
      agency = 'jmcf'
      agency_name = 'James Madison Council Fund'

    report = {
      'inspector': 'loc',
      'inspector_url': 'https://www.loc.gov/about/office-of-the-inspector-general/',
      'agency': agency,
      'agency_name': agency_name,
      'report_id': report_id,
      'url': report_url,
      'title': title,
      'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
      'estimated_date': True  # Unfortunately, all of these are estimates.
    }
    return report


def run(options):
  return LibraryOfCongressScraper(options).run()

utils.run(run) if (__name__ == "__main__") else None
