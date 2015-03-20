#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag, NavigableString
from utils import utils, inspector

archive = 2001

# options:
#   standard since/year options for a year range to fetch from.
#
#   pages - number of pages to fetch. defaults to all of them (using a very high number)
#
# Notes for IG's web team:
#   - Filters only work back through 2004, but there are documents back to 2001
#   - One landing page does not match the linked report, see
#     http://www.hudoig.gov/reports-publications/audit-reports/housing-authority-of-city-of-conyers-georgia-did-not-maintain

BASE_URL = 'http://www.hudoig.gov/reports-publications/results'
BASE_REPORT_PAGE_URL = "http://www.hudoig.gov/"
ARCHIVES_URL = "http://archives.hud.gov/offices/oig/reports/oigstate.cfm"
ALL_PAGES = 1000

# TODO: There is a set of reports which don't have pdfs linked for some reason
MISSING_REPORT_IDS = [
  "2012-CH-1008",
  "2012-FO-0005",
  "2011-NY-1010",
  "IED-11-003M",
  "2010-LA-1012",
  "2010-AO-1003",
  "2008-LA-1010",
  "2007-NY-1006",
  "SAR 52",
]

# These reports 404
BAD_LINKS = [
  'ig021803',
  "ig031004",
  'ig0701002',
  'ig131004',
  'ig131006',
  "ig141805",
  'ig231001',
  'ig231002',
  "ig231003",
  'ig231004',
  'ig331802',
  'ig351010',
  'ig351011',
  'ig351012',
  'ig351013',
  'ig351016',
  'ig351803',
  'ig431006',
  'ig451002',
  'ig581004',
  'ig631006',
  "ig770001",
  'ig851805',
  "oig31020",
  "oig31822",
]

UNRELEASED_TEXTS = [
  "appropriate for public disclosure",
  "not available to the public",
  "not for public release",
]

DUPLICATE_LANDING_PAGES = (
  "http://www.hudoig.gov/reports-publications/audit-reports-17",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/cheyenne-housing-authority-cheyenne-wyoming-improperly-awarded

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-huntington-park-huntington-park-california-did-not-alwa-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-huntington-park-huntington-park-california-did-not-always

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-new-rochelle-home-investment-partnership-program",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-new-rochelle-new-rochelle-new-york-had-administrative

  "http://www.hudoig.gov/reports-publications/audit-reports/holyoke-housing-authority%E2%80%99s-holyoke-massachusetts-lack-of",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/holyoke-housing-authoritys-holyoke-massachusetts-lack-of

  "http://www.hudoig.gov/reports-publications/audit-reports/richard-hutchens-and-associates-management-agent",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/richard-hutchens-associates-management-agent-buffalo-new-york

  "http://www.hudoig.gov/reports-publications/inspections-evaluations/follow-of-inspections-and-evaluations-division-its",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/follow-of-inspections-and-evaluations-division-its-inspection-of

  "http://www.hudoig.gov/reports-publications/inspections-evaluations/%C2%A0american-recovery-and-reinvestment-act-lessons-learned",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/american-recovery-and-reinvestment-act-lessons-learned-initiative

  "http://www.hudoig.gov/reports-publications/audit-reports/idaho-housing-and-finance-association-did-not-always-comply-hom-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/idaho-housing-and-finance-association-did-not-always-comply-home

  "http://www.hudoig.gov/reports-publications/audit-reports/lackawanna-municipal-housing-authority-lackawanna-new-york-need-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/lackawanna-municipal-housing-authority-lackawanna-new-york-needs

  "http://www.hudoig.gov/reports-publications/audit-reports/ameritrust-mortgage-bankers-inc-lake-success-ny-did-not",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/ameritrust-mortgage-bankers-inc-lake-success-ny-did-not-always

  "http://www.hudoig.gov/reports-publications/audit-reports/miami-dade-county-floridaneeds-strengthen-controls-over-its",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/miami-dade-county-florida-needs-strengthen-controls-over

  "http://www.hudoig.gov/reports-publications/audit-reports/miami-dade-housing-agency-miami-florida-did-not-maintain-adequa-1",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/miami-dade-housing-agency-miami-florida-did-not-maintain-adequate

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-miami-gardens-fl-did-not-adequately-support-salary-cost-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-miami-gardens-fl-did-not-adequately-support-salary-costs

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-troy-community-development-block-grant-program",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-troy-new-york-did-not-always-administer-its-community

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-rochester-new-york%E2%80%99s-management-controls-over-asset",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-rochester-new-yorks-management-controls-over-asset

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-newburgh-new-york-did-not-always-administer-its-communi-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-newburgh-new-york-did-not-always-administer-its community

  "http://www.hudoig.gov/reports-publications/audit-reports/polk-county-fl-did-not-comply-procurement-and",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/polk-county-fl-did-not-comply-procurement-and-contract

  "http://www.hudoig.gov/reports-publications/audit-reports/broward-county-fl-needs-strengthen-controls-over-its-neighborho-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/broward-county-fl-needs-strengthen-controls-over-its-neighborhood

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-west-palm-beach-fl-did-not-administer-its-community",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-west-palm-beach-fl-did-not-properly-administer-its

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-rochester-new-york%E2%80%99s-management-controls-over-asset",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-rochester-new-yorks-management-controls-over-asset

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-newburgh-new-york-did-not-always-administer-its-communi-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-newburgh-new-york-did-not-always-administer-its-community

  "http://www.hudoig.gov/reports-publications/audit-reports/all-american-home-mortgage-corp-brooklyn-ny-did-not-always-comp-0",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/all-american-home-mortgage-corp-brooklyn-ny-did-not-always-comply

  "http://www.hudoig.gov/reports-publications/audit-reports/adams-county-colorado-did-not-comply-home-investment-partnerships",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/adams-county-colorado-office-of-community-and-development-did-not

  "http://www.hudoig.gov/reports-publications/audit-reports/women%E2%80%99s-development-center-las-vegas-nv-charged-unallowable-flat",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/womens-development-center-las-vegas-nv-charged-unallowable-flat

  "http://www.hudoig.gov/reports-publications/audit-reports/city-of-fort-lauderdale-florida-did-not-properly-administer",
  # Duplicate of http://www.hudoig.gov/reports-publications/audit-reports/city-of-fort-lauderdale-florida-did-not-properly-administer-its
)

def run(options):
  pages = options.get('pages', ALL_PAGES)
  year_range = inspector.year_range(options, archive)

  all_reports = {}

  for page in range(1, (int(pages) + 1)):
    logging.debug("## Downloading page %i" % page)

    url = url_for(year_range, page=page)
    index_body = utils.download(url)
    index = BeautifulSoup(index_body)

    rows = index.select('div.views-row')

    if not rows:
      if page == 1:
        raise inspector.NoReportsFoundError("HUD (url)")
      else:
        # If no more reports found, quit
        break

    for row in rows:
      report = report_from(row, year_range)
      if report:
        key = (report["report_id"], report["landing_url"])
        if not key in all_reports:
          all_reports[key] = report
        else:
          # If we get the exact same landing page twice, skip it, nothing new
          # to see
          pass

  for key, report in all_reports.items():
    if key[1].endswith("-0"):
      dupe_key = (key[0], key[1][:-2])
      if dupe_key in all_reports:
        # If two reports have the same number, and their landing pages differ
        # by only an extra -0 added at the end, take the one without the -0
        continue
    inspector.save_report(report)

  archives_body = utils.download(ARCHIVES_URL)
  archives_page = BeautifulSoup(archives_body)
  state_links = archives_page.find("table", {"bgcolor": "CCCCCC"}). \
      table.find_all("a")
  if not state_links:
    raise AssertionError("No state links found for %s" % ARCHIVES_URL)
  for state_link in state_links:
    relative_url = state_link.get('href')
    state_name = state_link.text.strip()
    state_url = urljoin(ARCHIVES_URL, relative_url)
    state_body = utils.download(state_url)
    state_page = BeautifulSoup(state_body)
    state_container = state_page.h2.parent

    # N.B. split_dom is guaranteed to yield at least one element. If the
    # element doesn't have a number, title, and date, then report_from_archive()
    # will raise an exception. Thus, we don't need to explicitly check whether
    # at least one report was found.
    for result in split_dom(state_page, state_container, "hr"):
      link_list = result.find_all("a")
      if len(link_list) > 1:
        link_list = [link for link in link_list
                     if " ".join(link.text.split()) != "Auditee Reponse"]
        if len(link_list) > 1:
          raise Exception("Found multiple links on %s, scraper may be broken" \
              % state_url)
      report = report_from_archive(result, state_name, state_url, year_range)
      if report:
        inspector.save_report(report)

  do_canned_reports(year_range)

def split_dom(doc, tree, split_tag_name):
  '''This function takes a BeautifulSoup document, a subtree of that document,
  and the name of a tag. It returns a generator that rearranges the contents of
  the subtree, splitting the subtree at tags with the given name, and yielding
  a series of <div>s containing all tags between them. If the tag to split on
  occurs at multiple depths in the subtree, it will be flattened as needed to
  divide it up properly.'''
  accumulator = doc.new_tag("div")
  while len(tree):
    element = tree.contents[0].extract()
    if element.name == split_tag_name:
      yield accumulator
      accumulator = doc.new_tag("div")
    elif isinstance(element, Tag) and element.find(split_tag_name):
      # Recurse through this element and split its contents up
      first = True
      for temp in split_dom(doc, element, split_tag_name):
        if first:
          while len(temp):
            x = temp.contents[0].extract()
            accumulator.append(x)
        else:
          yield accumulator
          accumulator = temp
        first = False
    else:
      accumulator.append(element)
  yield accumulator

def type_from_report_type_text(report_type_text):
  if report_type_text in ["Audit Reports", 'Audit Guides']:
    return 'audit'
  elif report_type_text == 'Semiannual Reports':
    return 'semiannual_report'
  elif report_type_text == 'Conference Expenditures':
    return 'inspection'
  elif report_type_text in ['Inspections & Evaluations', 'Memorandums']:
    # Most of these look like investigations, but we should probably come back
    # and try to do some smarter parsing.
    return 'investigation'
  else:
    return 'other'

def report_from(report_row, year_range):
  published_date_text = report_row.select('span.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%B %d, %Y")

  landing_url_relative = report_row.select('a')[0]['href']
  landing_url = urljoin(BASE_REPORT_PAGE_URL, landing_url_relative)

  if landing_url in DUPLICATE_LANDING_PAGES:
    return

  if landing_url == "http://www.hudoig.gov/reports-publications/audit-reports/housing-authority-of-city-of-conyers-georgia-did-not-maintain":
    # Handle this elsewhere as a canned report
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("### Processing report %s" % landing_url)

  report_page_body = utils.download(landing_url)
  report_page = BeautifulSoup(report_page_body)

  article = report_page.select('article')[0]

  title = report_page.select('h1.title')[0].text
  report_type_text = article.select('div.field-name-field-pub-type div.field-item')[0].text
  report_type = type_from_report_type_text(report_type_text)

  try:
    report_id = article.select('div.field-name-field-pub-report-number div.field-item')[0].text.strip()
  except IndexError:
    # Sometimes the report_id is not listed on the page, so we fallback to
    # pulling it from the filename.
    report_filename = article.select('div.field-name-field-pub-document a')[0].text
    report_id = os.path.splitext(report_filename)[0]  # Strip off the extension

  # These both have filenames of "appendix", so we use different report IDs
  if landing_url == "http://www.hudoig.gov/reports-publications/audit-guides/chapter-1-appendix-attribute-sampling":
    report_id = "Attribute-Sampling"
  elif landing_url == "http://www.hudoig.gov/reports-publications/audit-guides/appendix-hud-regional-inspector-generals-audit":
    report_id = "HUD-Regional-Inspector-Generals-for-Audit"

  try:
    report_url = article.select('div.field-name-field-pub-document a')[0]['href']
  except IndexError:
    report_url = None

  def get_optional_selector(selector):
    try:
      text = article.select(selector)[0].text.strip()
      # don't return empty strings
      if text:
        return text
      else:
        return None
    except IndexError:
      return None

  summary = get_optional_selector('div.field-type-text-with-summary')

  unreleased = False
  # Some reports are not available to the general public.
  for text_string in UNRELEASED_TEXTS:
    if text_string in title.lower() or (summary and text_string in summary.lower()):
      unreleased = True
      break

  program_area = get_optional_selector('div.field-name-field-pub-program-area div.field-item')
  state = get_optional_selector('div.field-name-field-pub-state div.field-item')
  funding = get_optional_selector('div.field-name-field-related-to-arra div.field-item')

  missing = False
  if not report_url and not unreleased:
    if report_id in MISSING_REPORT_IDS:
      missing = True
      unreleased = True
    else:
      raise AssertionError("Report: %s did not have a report url and is not unreleased" % landing_url)

  report = {
    'inspector': 'hud',
    'inspector_url': 'http://www.hudoig.gov/',
    'agency': 'hud',
    'agency_name': 'Housing and Urban Development',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'landing_url': landing_url,
    'type': report_type,
    'program_area': program_area,
    'state': state,
    'summary': summary,
    'funding': funding
  }

  # only include these if they are true
  if unreleased:
    report['unreleased'] = True
  if missing:
    report['missing'] = True

  return report

ARCHIVE_ID_RE = re.compile("^(?:Audit|Audit\s+Report:?|Audit\s+Memorand(?:um|a)|AUDIT\s+MEMORANDUM|Audit-?\s*Related\s+Memorandum|AUDIT\s+RELATED\s+MEMORANDUM|Audit\s+Report\s+Memorandum|Memorandum|Audit\s+Case|Audit\s+Memorandum\s+Report|Memorandum\s+Report)\s*(?:No\\.?:?|No\\. No\\.|Number:?|:|#|\s)\s*([A-Z0-9][-A-Z0-9/ ]*[A-Z0-9])$")
ARCHIVE_DATE_RE = re.compile("^(?:\\.?I?ssued?\s+Date|Date\s+[Ii]ssued?|Issue)\s*:?\s+([A-Z][a-z]*) ([0-3]?[0-9]) ?, ([0-9]{4})$")
ARCHIVE_TITLE_RE = re.compile("^ ?(?:Titl?e|Subjec ?t): (.*[^ ]) ?$")

_seen_report_ids = set()

def report_from_archive(result, state_name, landing_url, year_range):
  report_link = result.a
  if report_link:
    relative_url = report_link.get('href')
    report_url = urljoin(landing_url, relative_url)
  else:
    report_url = None

  report_id = None
  published_on = None
  metadata_candidate = result.contents[0]
  while metadata_candidate.name != 'h3':
    if isinstance(metadata_candidate, NavigableString):
      text = metadata_candidate.strip()
      id_match = ARCHIVE_ID_RE.match(text)
      if id_match:
        report_id = id_match.group(1).replace('/', '-')
      date_match = ARCHIVE_DATE_RE.match(text)
      if date_match:
        published_on_text = " ".join(date_match.groups())
        published_on = datetime.datetime.strptime(published_on_text, "%B %d %Y")
      if report_id and published_on:
        break
    metadata_candidate = metadata_candidate.next_element
  if not report_id:
    raise Exception("Could not find audit report number on %s\n%s" % (landing_url, result.contents[:5]))
  if not published_on:
    raise Exception("Could not find audit report date on %s\n%s" % (landing_url, result.contents[:5]))

  title_raw = re.sub("\s+", " ", result.h3.text)
  title = ARCHIVE_TITLE_RE.match(title_raw).group(1)
  summary = '\n'.join([re.sub("\s+", " ", p.text).strip()
                       for p in result.find_all("p")])

  if report_url == "http://archives.hud.gov/offices/oig/reports/files/ig531001.pdf":
    # Fix typo
    report_id = "2005-PH-1001"
  elif report_url == "http://archives.hud.gov/offices/oig/reports/files/ig341801.pdf":
    # Fix typo
    report_id = "2003-AT-1801"
  elif report_url == "http://archives.hud.gov/offices/oig/reports/files/ig231801.pdf":
    # Fix typo
    report_id = "2002-PH-1801"
  elif report_url == "http://archives.hud.gov/offices/oig/reports/files/ig251802.pdf" and title == "Partners for Community Development, Inc., Home Buyers-Lease Purchase HOME Rehabilitation and Accessibility Programs, Sheboygan, Wisconsin":
    # This report has the wrong number and link
    report_url = None
    report_id = report_id + "-WI"
  elif report_id in _seen_report_ids and report_id in (
      "97-FW-222-1802",
      "98-SE-202-1002",
      "97-AT-203-1805",
  ):
    # These reports show up on two pages
    return
  _seen_report_ids.add(report_id)

  report = {
    'inspector': 'hud',
    'inspector_url': 'http://www.hudoig.gov/',
    'agency': 'hud',
    'agency_name': 'Housing and Urban Development',
    'report_id': report_id,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'landing_url': landing_url,
    'type': "audit",
    'state': state_name,
    'summary': summary,
  }
  if report_url:
    report['url'] = report_url
  else:
    report['unreleased'] = True
  if report_id in BAD_LINKS:
    report['unreleased'] = True
    report['missing'] = True
    report['url'] = None
  return report

def url_for(year_range, page=1):
  start_year = year_range[0]
  end_year = year_range[-1]
  if start_year < 2004:
    # The website believes it doesn't have any reports before 2004. If we are
    # requesting before that time, remove all date filters and we will later
    # filter the results in memory
    start_year, end_year = '', ''
  return '%s?keys=&date_filter[min][year]=%s&date_filter[max][year]=%s&page=%i' % (BASE_URL, start_year, end_year, page-1)

def do_canned_reports(year_range):
  report = {
    'inspector': 'hud',
    'inspector_url': 'http://www.hudoig.gov/',
    'agency': 'hud',
    'agency_name': 'Housing and Urban Development',
    'report_id': '2009-AT-1011',
    'url': 'http://www.hudoig.gov/sites/default/files/documents/audit-reports/ig0941011.pdf',
    'title': 'The City of Miami, Florida, Did Not Properly Administer Its Community Development Block Grant Program',
    'published_on': '2009-08-18',
    'landing_url': 'http://www.hudoig.gov/reports-publications/audit-reports/housing-authority-of-city-of-conyers-georgia-did-not-maintain',
    'type': 'audit',
    'program_area': 'Public and Indian Housing',
    'state': 'Georgia'
  }
  if 2009 in year_range:
    inspector.save_report(report)

utils.run(run) if (__name__ == "__main__") else None
