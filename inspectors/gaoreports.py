#!/usr/bin/env python

import datetime
import logging
import json
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

"""
Not the GAO IG, but the GAO itself, who publishes an amazing number of
excellent reports:

* Reports
* Restricted (unreleased) reports
    http://www.gao.gov/restricted/restricted_reports

* Bid protest decisions, for which @vzvenyach wrote a Python scraper
    https://github.com/vzvenyach/gao
This is not included here but could be added in easily enough if it
is believed that they are sufficiently "oversighty" to fit here.

* Open recommendations
    http://www.gao.gov/recommendations
I wrote a scraper for this but did not include it because I believe they are
likely not be the best fit for this repository, in part because we already have
the reports the recs come from and because they may eventually close.

Report pages don't break out which agency they pertain to, if any, so this
lists GAO as both the inspector and the agency. However, they are mapped
internally, as they are browsable by agency here:
http://www.gao.gov/browse/agency/Executive

"""

# https://www.gao.gov

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# Not sure if the gao.gov/api/ interface is documented anywhere?
# It seems hit-or-miss because only one unpredictable version of
# the report--highlights, full report, etc,--gets the complete JSON response,
# while the others are missing URLs. Ideally you could pass a date range
# to the API and get an index. We found it more useful to rely on the html
# pages instead where possible here.


def run(options):

  scrape_reports(options)
  scrape_restricted_reports(options)


def scrape_reports(options):
  """Pull reports from "Reports and Testimonies - Browse by date" web page."""

  REPORTS_URL = 'http://www.gao.gov/browse/date/custom?adv_begin_date=01/01/' +\
    '%s&adv_end_date=12/31/%s&rows=50&o=%s' # % (year, year, offset)
  archive = 1970
  # Amazingly, reports go back to 1940, though those are unlikely to be
  # legible enough to OCR. Also very cool, even 1950s-era reports seem to have
  # a highlightable embedded text layer in them. Of course, it was the
  # General Accounting Office back then and less oversighty.

  year_range = inspector.year_range(options, archive)
  for year in year_range:
    is_next_page = True
    offset = 0
    while is_next_page:
      doc = utils.beautifulsoup_from_url(
        REPORTS_URL % (year, year, offset))
      results = doc.select("div.listing")
      for result in results:
        report = process_report(result, year_range)
        if report:
          inspector.save_report(report)
      page_links = doc.select("a.non-current_page")
      if len(page_links) and page_links[-1].text.startswith('Next'):
        offset += 50
      else:
        is_next_page = False


def process_report(result, year_range):

  """Use the report ID obtained from HTML to hit GAO's API"""
  # <a href="/assets/690/685452.pdf">View Report (PDF, 8 pages)</a>
  # 685452 is the ID used by the API.

  # The link's path looks like "/products/GAO-17-558", use the last part
  # as the report ID
  landing_url = urljoin('https://www.gao.gov', result.a['href'])
  report_number = os.path.basename(result.a['href'])

  title = re.sub("\\s+", " ", result.span.text).strip()
  description = re.sub("\\s+", " ", result.p.text).strip()

  dates = result.find_all('span')[-1].string.replace('\n', '').split(': ')
  # ['Published', 'Mar 31, 1959. Publicly Released', 'Mar 31, 1959.']
  # Prefer the first, fall back to the latter if necessary--not sure it ever is
  published_on = parse_date(dates[1].split('.')[0].strip())
  if not published_on:
    published_on = parse_date(dates[-1].replace('.', '').strip())

  if not published_on:
    admin.log_no_date("gaoreports", report_number, title, landing_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  pdf_links = result.find_all('li', {'class': 'pdf-link'})
  (report_url, highlights_url, accessible_url) = (None, None, None)
  for link in pdf_links:
    if not link.a or link.a['href'] == '':
      continue
    if 'View Report' in link.a.string:
      report_url = urljoin('https://www.gao.gov', link.a['href'])
    if 'Highlights' in link.a.string:
      highlights_url = urljoin('https://www.gao.gov', link.a['href'])
    if 'Accessible' in link.a.string:
      accessible_url = urljoin('https://www.gao.gov', link.a['href'])
  # Last PDF is full report. First one could be Highlights.
  try:  # get the ID from one of the filenames, minus the extension
    api_id = os.path.splitext(os.path.basename(pdf_links[-1].a['href']))[0]
  except Exception:  # very old reports are sometimes different
    api_id = os.path.splitext(os.path.basename(result.a['href']))[0]
  api_id = api_id.lstrip('0')

  if not landing_url and not report_url:
    logging.debug("[%s] No landing URL or PDF, skipping..." % api_id)
    return None

  api_url = "http://www.gao.gov/api/id/%s" % api_id
  json_response = json.loads(utils.download(api_url))
  if not json_response:
    return None
  details = json_response[0]

  """looks like this {
    "youtube_id": null,
    "type": "reports",
    "content_id": "685451",
    "bucket_term": "Defense Management",
    "title": "DOD Has Taken Initial Steps to Formulate",
    "description": null,
    "rptno": "GAO-17-523R",
    "docdate": "2017-06-23",
    "actual_release_date": "2017-06-23T12:00:00Z",
    "actual_release_date_formatted": "Jun 23, 2017",
    "original_release_dt": null,
    "category_img": "http://www.gao.gov/images/rip/defense.jpg",
    "category_img_alt": "defense icon",
    "additional_links": "",
    "topics": [
    "National Defense"
    ],
    "subsite": [
    "Correspondence"
    ],
    "format": null,
    "mime_type_s": null,
    "ereport_flag": 0,
    "pdf_url": "http://www.gao.gov/assets/690/685452.pdf",
    "url": "http://www.gao.gov/products/GAO-17-523R",
    "document_type": "report",
    "supplement_url": null,
    "description_short": ""
    },"""

  if 'html_url' in details:
    accessible_url = details['html_url']
  categories = details.get('topics', None)
  if not categories:  # json could have null or []
      categories = []
  if details['bucket_term']:
    categories.append(details['bucket_term'])
  # defer to HTML instead of API for this stuff
  # published_on = details['docdate']
  # posted_at = details['actual_release_date'][:10]
  # title = details['title']
  # report_type = details['document_type']
  # if details.get('description', None):
  #   description = details['description']

  report = {
    'inspector': 'gaoreports',
    'inspector_url': 'https://www.gao.gov',
    # often GAO reports do focus on a program in a specific external agency,
    # but we're not attempting to discern it.
    # We'll just have GAO for the inspector and the agency.
    'agency': 'gao',
    'agency_name': 'Government Accountability Office',
    'report_id': report_number,
    'landing_url': landing_url,
    'url': report_url,
    'title': title,
    'type': details['document_type'],
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),

    'highlights_url': highlights_url,
    'accessible_url': accessible_url,
    'description': description,
    'categories': categories,
    'category_img': details['category_img'],
    'category_img_alt': details['category_img_alt'],
    'subsite': details['subsite']
  }

  if not report_url:
    report['unreleased'] = True

  return report


def scrape_restricted_reports(options):
  """Restricted Products.

  A single HTML page lists unreleased reports since 2014, with no links."""

  # These reports are unreleased -- we could make this the text?
  """The following products have been determined to contain either
classified information or controlled unclassified information by the audited
agencies and cannot be publicly released.

Members of Congress or congressional staff who wish to obtain one or more of
these products should call or e-mail the Congressional Relations Office.
All others who wish to obtain one or more of these products should follow the
instructions found on Requesting Restricted Products."""

  REPORTS_URL = 'http://www.gao.gov/restricted/restricted_reports'
  archive = 2014

  year_range = inspector.year_range(options, archive)
  doc = utils.beautifulsoup_from_url(REPORTS_URL)
  results = doc.select("div.listing")
  for result in results:
    report = process_restricted_report(result, year_range, REPORTS_URL)
    if report:
      inspector.save_report(report)


def process_restricted_report(div, year_range, REPORTS_URL):

  title = div.contents[0]
  span = div.div.span.string.strip()
  report_number = span.split(': ')[0]
  report_date = parse_date(span.split(': ')[-1])

  if not report_date:
    admin.log_no_date("gaoreports", report_number, title)
    return

  if report_date.year not in year_range:
    return None

  report = {
    'inspector': 'gaoreports',
    'inspector_url': 'https://www.gao.gov',
    # often GAO reports do focus on a program in a specific external agency,
    # but we're not attempting to discern it in a structured way.
    # We'll just have GAO for the inspector and the agency.
    'agency': 'gao',
    'agency_name': 'Government Accountability Office',
    'report_id': report_number,
    'unreleased': True,
    'landing_url': REPORTS_URL,
    'title': title,
    'type': 'Unreleased report',
    'published_on': datetime.datetime.strftime(report_date, "%Y-%m-%d"),

  }

  return report


def parse_date(report_date_str):
  try:
    report_date = datetime.datetime.strptime(report_date_str, "%B %d, %Y")
  except ValueError:
    try:
      report_date = datetime.datetime.strptime(report_date_str, "%b %d, %Y")
    except ValueError:
      return None
  return report_date


utils.run(run) if (__name__ == "__main__") else None
