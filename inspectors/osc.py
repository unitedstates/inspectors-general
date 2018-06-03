#!/usr/bin/env python

import datetime
import logging

from bs4 import BeautifulSoup
from utils import utils, inspector

# Office of Special Counsel investigates whistleblower retaliation at all agencies, so unlike most parsers in this project, agency will be different from inspector

# https://osc.gov/Pages/Resources-PublicFiles.aspx
archive = 2009  # OSC began posting public files in 2009

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# Styling is all inline making for bloated tables. CSS classes would be a better solution.

REPORTS_URL_FORMAT_1 = 'https://osc.gov/Pages/PublicFiles-FY%s.aspx'
REPORTS_URL_FORMAT_2 = 'https://osc.gov/Pages/Public-Files-FY%s.aspx'

REPORT_TYPES = (  # there can be multiple files within each type. The integer is the index of the column these appear in the table.
    (6, 'Letter to President'),
    (7, 'Analysis'),
    (8, 'Agency Report'),
    (9, 'Whistleblower Comments'),
    (10, 'Unknown'),   # These lines are a hack for 3 or 4 cases in 2009, when cells were sometimes sub-divided horizontally
    (11, 'Unknown'),   # instead of stacking multiple PDFs vertically with <br/>s. So this just handles a few cases where there are two
                       # extra columns that might have PDFs in them

)


"""
These are the outcome codes as of 2015, but let's generate this dynamically, in case it changes

OUTCOME_CODES = { #there can be several for each case
  '10':    'Changes in agency rules, regulations, policy or practices',
  '20':    'Restoration of any aggrieved employee',
  '30':    'Disciplinary action against any employee',
  '40':    'Referral of criminal matter to the Attorney General',
  '50':    'Other actions',
  '60':    'Totally unsubstantiated',
  '70':    'Cost Savings to the Government',
  '80':    'Improved Health and/or Safety',
  '90':    'Special Counsel found report not reasonable'
}
"""


# take a beautifulsoup document and parse the list of outcome codes from the first table, returning a dict like the one above
def generate_outcome_codes(doc):
  OUTCOME_CODES = {}
  table = doc.find('table')
  cells = table.findAll('td')
  for i, td in enumerate(cells):
    # use odd and even pairs to parse the table, which has four columns like (key,value,key,value)
    if i % 2 == 1 and td.text != '':
      OUTCOME_CODES[cells[i - 1].text.strip()] = td.text.strip()
  return OUTCOME_CODES


def url_for_year(year):
  if year == 2018:
    return REPORTS_URL_FORMAT_2 % year
  return REPORTS_URL_FORMAT_1 % year


def run(options):
  year_range = inspector.year_range(options, archive)
  report_flag = False

  # Pull the table of reports for each year
  for year in year_range:
    url = url_for_year(year)
    html = utils.download(url, scraper_slug="osc")

    if html is None:
      if year == max(year_range):
        continue
      else:
        raise Exception("Couldn't fetch reports page {}".format(url))

    #  spaces appear as &#160; and \u200b .... fix that now
    html = html.replace('&#160;', ' ').replace('\u200b', ' ').replace('\u00a0', ' ').replace('\r', '').replace('\n', '')
    doc = BeautifulSoup(html, "lxml")

    OUTCOME_CODES = generate_outcome_codes(doc)

    keys_used = []  # a few reports appear multiple times... ignore them the second time if they appear more than once

    results = doc.findAll("table")[1].tbody.findAll('tr')  # no ids on the tables, but it's the second one
    for result in results:
      reports = report_from(result, year, year_range, url, OUTCOME_CODES)
      for report in reports:
        if report['report_id'] not in keys_used:
          inspector.save_report(report)
          keys_used.append(report['report_id'])
          report_flag = True

  if not report_flag:
    raise inspector.NoReportsFoundError("OSC")

previous_report = None  # global variable to let us see the previous row in case the following one needs to reference it


# takes a row in the table (one group of related PDFs) and extracts them into
# a list of dicts of details that are ready for inspector.save_report().
def report_from(result, year, year_range, landing_url, OUTCOME_CODES):
  """
  columns are:
  OSC File     #    part 1
  OSC File     #    part 2
  Agency       #   not standardized, may be formatted different ways or include subagency name in different ways
  Location
  Date Closed  #   03-27-2015
  Result Code  #   comma-separated numbers mapping to one or more OUTCOME_CODES above describing the results of the probe
  Ltr to Pres  #   One or more PDFs
  Analysis     #   One or more PDFs
  Agency Rpt   #   One or more PDFs
  WB CMT       #   One or more PDFs (whistleblower comments)

  """

  global previous_report
  reports = []

  cells = result.findAll('td')
  case_num_short = cells[0].text.strip()  # ID is sufficiently unique for one group of PDFs (row in the table)

  if len(cells) < 10 or case_num_short == '':  # there are a few gnarly colspan=2s that throw things off
    return fix_partial_row(cells, previous_report)

  case_num_long = cells[1].text.strip()  # There can be one or more case_nums for one group of PDFs (row in the table) but they do not uniquely identify individual PDFs any better than ID
  agency_name = cells[2].text.strip()
  location = cells[3].text.strip()
  date = cells[4].text.strip()
  # if the date is missing for some reason, set it to the first day of the year it was published
  try:
    published_on = datetime.datetime.strptime(date, '%m-%d-%Y')
  except:
    published_on = datetime.datetime(year, 1, 1)

  results = cells[5].text
  result_codes = [OUTCOME_CODES[x.strip()] for x in results.split(',') if x.strip() in OUTCOME_CODES]

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % id)
    return []

  # the first PDF in a table's row is the Letter to the President. Link back to this one on all the supplemental ones to provide context
  main_letter_url = None

  # loop through the four right-most columns described above to look for PDFs. Report_type_name is the name of the column
  for (column_index, report_type) in REPORT_TYPES:
    if column_index >= len(cells):
      continue
    pdfs = cells[column_index].findAll('a')
    # there might be multiple PDFs per cell (if whistleblowers gave comments in two parts, or there is a supplemental report, etc)
    for i, pdf_link in enumerate(pdfs):
      report_url = 'https://osc.gov%s' % pdf_link['href']
      if not main_letter_url:
        main_letter_url = report_url
      # extra_descrip is the short blurb of text that appears above the PDF icon when there is more than one PDF in a cell
      extra_descrip = get_extra_descrip(pdf_link)

      # OSC reports don't have descriptive titles, so make one from the other fields
      title = '%s | %s | %s | %s' % (agency_name, location, case_num_short, report_type)
      if extra_descrip != '':
        try:
          title = title + ' | ' + extra_descrip
        except:
          pass

      # make a unique id out of the PDF URL
      report_id = make_report_id(pdf_link['href'])

      report = {
        'inspector': 'osc',
        'inspector_url': 'https://osc.gov',  # The IG's primary website URL.
        'agency': 'OSC',                     # This will always be OSC since the report's target investigation isn't standardized in any way
        'agency_name': agency_name,          # This, on the other hand, will be the name of the agency, department or office that the OSC report is about
        'report_id': report_id,
        'url': report_url,
        'title': title,
        'type': report_type,                 # Letter to president, Analysis, etc., from tuple above
        'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),  # Date of publication
        'landing_url': landing_url,          # The OSC web page listing investigations for the year this one occurred
        'unreleased': False,
        'case_num_short': case_num_short,
        'case_num_long': case_num_long,
        'outcomes': result_codes,
        'main_letter_url': main_letter_url
      }

      reports.append(report)
      previous_report = report

  return reports


def make_report_id(url):
  return inspector.slugify(url.replace('/PublicFiles/', '').replace('/publicfiles/', '').replace('.pdf', ''))


def get_extra_descrip(pdf_link):
  # takes a beautifulsoup object representing a PDF and tries to find the blurb of text that may be right above it.
  # this seems to be hand-coded HTML so we just have to look around a bit.
  # usually blank, sometimes 'supplemental report' or 'comments 1', 'comments 2', etc. to differentiate between PDFs if there are multiple in this cell.
  # we'll look for any plain text, until we get to the end of the cell or the preceding PDF link.

  def is_tag(bs_element):
    try:
      bs_element.name
      return True
    except:
      return False

  extra_descrip = ''

  previous_element = pdf_link
  keepchecking = True
  while keepchecking:
    if previous_element.previousSibling:
      previous_element = previous_element.previousSibling
    else:
      keepchecking = False
      break
    element_string = str(previous_element).strip()
    if element_string.startswith('<a '):
      keepchecking = False
    elif element_string != '' and not element_string.startswith('<'):
      extra_descrip = element_string + ' ' + extra_descrip

  extra_descrip = extra_descrip.strip()
  return extra_descrip


def fix_partial_row(cells, previous_report):
  # deal with a few rows from very old years where colspans and rowspans are used, leaving seemingly orphaned PDFs.
  # for these, the PDFs will (as they should) get their metadata from the previous full row.

  reports = []
  report = previous_report

  title_chunks = report['title'].split(' | ')
  location = title_chunks[1]

  for cell in cells:
    for a in cell.findAll('a'):
      if not a['href'].upper().endswith('.PDF'):
        continue

      title = '%s | %s | %s | %s' % (report['agency_name'], location, report['case_num_short'], 'Unknown')
      report['url'] = 'https://osc.gov%s' % a['href']
      report['report_id'] = make_report_id(a['href'])
      report['type'] = 'Unknown'
      extra_descrip = get_extra_descrip(a)

      if extra_descrip != '':
        try:
          title = title + ' | ' + extra_descrip
        except:
          pass
      report['title'] = title

      reports.append(report)
      previous_report = report

  return reports


utils.run(run) if (__name__ == "__main__") else None
