#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://www.sba.gov/office-of-inspector-general
archive = 1994

# options:
#   standard since/year options for a year range to fetch from.
#
#   pages - number of pages to fetch. defaults to all of them (using a very high number)
#
# Notes for IG's web team:
# - Add the published date for all reports in `REPORT_PUBLISHED_MAPPING`.

REPORTS_AJAX_URL = "https://www.sba.gov/views/ajax"
BASE_REPORT_URL = "https://www.sba.gov/"

REPORT_LABEL_REGEX = re.compile("Report Number")

REPORT_PUBLISHED_MAPPING = {
  "-oig_recovery_oversightframewrk_1": datetime.datetime(2009, 3, 11),
  "-oig_recovery_work_plan_1": datetime.datetime(2009, 11, 1),
  "ROM-11-03": datetime.datetime(2011, 3, 2),
}

# These landing pages have duplicated reports, so skip these and save the other
DUPLICATE_LANDING_URLS = (
  "https://www.sba.gov/content/rom10-13-memorandum-adequacy-procurement-staffing-and-oversight-contractors-supporting-procurement-function",
  "https://www.sba.gov/content/advisory-memorandum-7-32",
  "https://www.sba.gov/content/advisory-memorandum-4-11-sba%E2%80%99s-federal-agencies%E2%80%99-centralized-trail-balance-system-facts-da-0",
  "https://www.sba.gov/content/advisory-memorandum-3-11-sba%E2%80%99s-federal-agencies%E2%80%99-centralized-trial-balance-systems-facts-d-1",
  "https://www.sba.gov/content/advisory-memorandum-3-11-sba%E2%80%99s-federal-agencies%E2%80%99-centralized-trial-balance-systems-facts-d-2",
  "https://www.sba.gov/oig/audit-report-2-33-audit-7j-management-and-technical-assistance-program-agreement-administration",
  "https://www.sba.gov/content/advisory-memorandum-2-28-independent-evaluation-sba%E2%80%99s-information-security-program-0",
  "https://www.sba.gov/content/advisory-memorandum-a1-05-sba%E2%80%99s-use-government-cars-and-hired-car-services-0",
  "https://www.sba.gov/content/audit-report-1-18-independent-accountant%E2%80%99s-report-performance-audit-farmington-casualty-co-0",
  "https://www.sba.gov/content/advisory-memorandum-01-04-01-results-management-challenges-working-group-discussions-0",
  "https://www.sba.gov/content/audit-report-0-15-audit-sba%E2%80%99s-proposed-systems-development-methodology-0",
  "https://www.sba.gov/content/audit-report-0-02-audit-sba%E2%80%99s-fy-1998-financial-statements-management-letter-0",
)

# This will actually get adjusted downwards on the fly, so pick a huge number.
# There are 49 pages total as of 2014-08-12, so 1000 should be okay.
ALL_PAGES = 1000

def run(options):
  year_range = inspector.year_range(options, archive)

  # Suggested flow, for an IG which paginates results.
  pages = options.get('pages', ALL_PAGES)
  for page in range(1, (int(pages) + 1)):
    data = {
      'view_name': 'oig_nodes',
      'view_display_id': 'block_search_oig_reports',
    }
    if page:
      # Only add page= if page > 0
      data['page'] = page


    response = utils.post(REPORTS_AJAX_URL,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    if not response:
      raise Exception("Failed to fetch data from sba.gov.")

    page_html = response.json()[1]['data']
    doc = BeautifulSoup(page_html)
    results = doc.select("tr")
    if not results:
      if page == 1:
        raise inspector.NoReportsFoundError("Small Business Admininstration")
      else:
        break

    for index, result in enumerate(results):
      if not index:
        # Skip the header row
        continue
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)

def report_type_from_text(text):
  if text == 'Press Releases':
    return 'press'
  elif text == 'Congressional Testimony':
    return 'testimony'
  elif text == 'Top Management Challenges':
    return 'management_challenges'
  elif text == 'Semi-Annual Reports to Congress':
    return 'semiannual_report'
  elif any(type_text in text for type_text in [
    'Recent Investigative & Audit Actions',
    "Business Loans and Lender Oversight",
    "Disaster Loans",
    "Surety Bonds",
    "SBICs",
    "Government Contracting and Business Development",
    "Entrepreneurial Development",
    "Agency Management",
    "External Quality Control Reviews of the OIG",
  ]):
    return 'audit'
  else:
    return 'other'

def report_from(result, year_range):
  published_on_text = result.select("td")[0].text.strip()
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%Y-%m-%d')
  except ValueError:
    published_on = None

  report_type_text = result.select("td")[3].text.strip()
  report_type = report_type_from_text(report_type_text)

  # we don't always have the published_on yet, but if so we can
  # check and short-circuit
  if published_on and published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % published_on_text)
    return

  title = result.select("td")[2].text.strip()
  title_prefixer = re.compile("(Audit|Report)\\s*(Number|Report)\\s*[\\d\\-]+:\\s*", re.I)
  title = title_prefixer.sub("", title)

  landing_url = urljoin(BASE_REPORT_URL, result.find("a").get('href'))

  if landing_url in DUPLICATE_LANDING_URLS:
    return

  landing_body = utils.download(landing_url)

  if landing_body is None:
    logging.warn("Bad landing URL, downloaded None: %s" % landing_url)
    raise Exception("Couldn't download landing URL.")

  landing_page = BeautifulSoup(landing_body)

  try:
    report_url = urljoin(BASE_REPORT_URL, landing_page.select("#attachments a")[0].get('href'))
  except IndexError:
    # Some 'reports' don't have attachments.
    # https://www.sba.gov/oig/audit-report-14-05-independent-auditors-report-sbas-fy-2013-special-purpose-financial-statements
    report_url = landing_url

  file_type = None
  if not report_url.endswith(".pdf"):
    file_type = 'html'

  report_filename = report_url.split("/")[-1]

  report_id_node = landing_page.find("div", class_="field-label", text=REPORT_LABEL_REGEX)
  if report_id_node:
    report_id = "-".join(report_id_node.find_next("div", class_="field-item").text.split())
    report_id = report_id.replace(':', '')
    if report_id.startswith('9-'):
      report_id = '%s %d' % (report_id, published_on.year)
  else:
    report_filename_without_extension, extension = os.path.splitext(report_filename)
    report_filename_slug = "-".join(report_filename_without_extension.split())[:43]
    report_id = "{}-{}".format(published_on_text, report_filename_slug)

  # This report is mislabeled on the landing page and in the PDF filename.
  # If you open the PDF, the cover page says "Report No. 5-01."
  if landing_url == "https://www.sba.gov/content/fiscal-year-2005-report-most-serious-management-and-performance-challenges-facing-small-business-administration":
    report_id = "5-01"

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]

  if not published_on:
    try:
      # For Spring reports, use April. For Fall reports, use October.
      published_on_text = re.sub("(?i)Spring", "April", report_filename)
      published_on_text = re.sub("(?i)Fall", "October", published_on_text)

      # published_on_text = report_filename.replace("Spring", "April").replace("Fall", "October")
      published_on_text = "".join(re.search('([a-zA-Z0-9]+)[_\-\s]*(\d{4})', published_on_text).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B%Y')
    except (ValueError, AttributeError):
      try:
        published_on = datetime.datetime.strptime(published_on_text, '%b%Y')
      except ValueError:
        try:
          fiscal_year = re.search('FY(\d+)', report_id, re.IGNORECASE).groups()[0]
          published_on = datetime.datetime.strptime("November {}".format(fiscal_year), '%B %y')
        except AttributeError:
          try:
            fiscal_year = re.search('FY(\d+)', published_on_text, re.IGNORECASE).groups()[0]
            published_on = datetime.datetime.strptime("November {}".format(fiscal_year), '%B %Y')
          except (AttributeError, ValueError):
            published_on_text = re.search('([a-zA-Z0-9]+\d)', published_on_text).groups()[0]
            published_on = datetime.datetime.strptime(published_on_text, '%b%y')

  # okay, now there's *definitely* a published_on
  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_id)
    return

  report = {
    'inspector': 'sba',
    'inspector_url': 'https://www.sba.gov/office-of-inspector-general',
    'agency': 'sba',
    'agency_name': 'Small Business Administration',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if file_type:
    report['file_type'] = file_type
  return report

utils.run(run) if (__name__ == "__main__") else None
