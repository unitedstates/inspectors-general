#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from utils import utils, inspector

# https://oig.hhs.gov/reports-and-publications/index.asp
# Oldest report: 1985

# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated, which
#            correspond to the topics defined on the site. For example:
#            'OAS,OE'
#            Defaults to all topics.
#
#            OAS  - Office of Audit Services
#            OE   - Office of Evaluation and Inspections
#            HCF  - Health Care Fraud and Abuse Control Program Report
#            SAR  - Semiannual Reports to Congress
#            MIR  - Medicaid Integrity Reports
#            TMPC - Top Management & Performance Challenges
#            CPR  - Compendium of Priority Recommendations
#            SP   - Strategic Plan
#            WP   - Work Plan
#            POR  - Portfolio and Other Reports
#            FOIA - Freedom of Information Act (FOIA)
#            FRN  - Federal Register Notices
#            RA   - Regulatory Authorities
#            B    - OIG Budget
#            RAOR - Recovery Act Oversight Reports
#            RAA  - Recovery Act-related Audit and Inspection Reports

# Notes for IG's web team:
#  - A large number of reports don't list a date when they were published.
#  See "Adverse Events in Hospitals: Medicare's Responses to Alleged Serious
#  Events"(OEI-01-08-00590) referenced at
#  https://oig.hhs.gov/reports-and-publications/oei/a.asp
#  As a fallback, this scraper uses the HTTP Last-Modified header for reports
#  published after 2002. For reports published before 2002, we use the report id
#  month-year as an approximation of the published date.
#  - Fix published date for http://oig.hhs.gov/oas/reports/region3/31200010.asp
#  on http://oig.hhs.gov/reports-and-publications/oas/cms.asp. It currently
#  says 08-03-2102
#  - Fix published date for https://oig.hhs.gov/oei/reports/oei-06-98-00321.pdf
#  on https://oig.hhs.gov/reports-and-publications/oei/s.asp. It currently
#  says Dec 2028.
#  - Fix published date for https://oig.hhs.gov/oas/reports/region7/70903133.asp
#  It currently says 14-21-2010.
#  - Fix published date for https://oig.hhs.gov/oas/reports/region3/31300031.asp
#  It currently says 03-05-2015.
#  - Fix published date for https://oig.hhs.gov/oas/reports/region9/91102005.asp
#  It currently says 04-23-3012.
#  - Add missing report for 'Use of Discounted Airfares by the Office of the Secretary' (A-03-07-00500)
#  linked to from https://oig.hhs.gov/reports-and-publications/oas/dept.asp
#  - The report https://oig.hhs.gov/oas/reports/region5/50800067.asp returns a 500.

TOPIC_TO_URL = {
  "OAS": 'https://oig.hhs.gov/reports-and-publications/oas/index.asp',
  "OE": 'https://oig.hhs.gov/reports-and-publications/oei/subject_index.asp',
  "HCF": 'https://oig.hhs.gov/reports-and-publications/hcfac/index.asp',
  "SAR": 'https://oig.hhs.gov/reports-and-publications/semiannual/index.asp',
  "MIR": 'https://oig.hhs.gov/reports-and-publications/medicaid-integrity/index.asp',
  "TMPC": 'https://oig.hhs.gov/reports-and-publications/top-challenges/',
  "CPR": 'https://oig.hhs.gov/reports-and-publications/compendium/index.asp',
  "SP": 'https://oig.hhs.gov/reports-and-publications/strategic-plan/index.asp',
  "WP": 'https://oig.hhs.gov/reports-and-publications/workplan/index.asp',
  "POR": 'https://oig.hhs.gov/reports-and-publications/portfolio/index.asp',
  "FOIA": 'https://oig.hhs.gov/reports-and-publications/foia/index.asp',
  "FRN": 'https://oig.hhs.gov/reports-and-publications/federal-register-notices/index.asp',
  "RA": 'https://oig.hhs.gov/reports-and-publications/regulatory-authorities/index.asp',

  "B": 'https://oig.hhs.gov/reports-and-publications/budget/index.asp',
  # "RAOR": 'https://oig.hhs.gov/reports-and-publications/recovery/index.asp',
  "RAA": 'https://oig.hhs.gov/reports-and-publications/recovery/recovery_reports.asp',
}

TOPIC_TO_ARCHIVE_URL = {
  "OAS": 'https://oig.hhs.gov/reports-and-publications/archives/oas/index.asp',

  # Some reports missing published dates
  # "SAR": 'https://oig.hhs.gov/reports-and-publications/archives/semiannual/index.asp',

  # Some reports missing published dates
  # "TMPC": 'https://oig.hhs.gov/reports-and-publications/archives/top-challenges/index.asp',

  # No published dates
  # "CPR": 'https://oig.hhs.gov/reports-and-publications/archives/compendium/redbook.asp',

  # Some reports missing published dates
  # "WP": 'https://oig.hhs.gov/reports-and-publications/archives/workplan/index.asp',

  "FRN": 'https://oig.hhs.gov/reports-and-publications/archives/federal-register-notices/index.asp',
  "B": 'https://oig.hhs.gov/reports-and-publications/archives/budget/index.asp',
}

TOPIC_NAMES = {
  "OAS": 'Office of Audit Services',
  "OE": 'Office of Evaluation and Inspections',
  "HCF": 'Health Care Fraud and Abuse Control Program Report ',
  "SAR": 'Semiannual Reports to Congress',
  "MIR": 'Medicaid Integrity Reports',
  "TMPC": 'Top Management & Performance Challenges',
  "CPR": 'Compendium of Priority Recommendations',
  "SP": 'Strategic Plan',
  "WP": 'Work Plan',
  "POR": 'Portfolio and Other Reports',
  "FOIA": 'Freedom of Information Act (FOIA)',
  "FRN": 'Federal Register Notices',
  "RA": 'Regulatory Authorities',
  "B": 'OIG Budget',
  "RAOR": 'Recovery Act Oversight Reports',
  "RAA": 'Recovery Act-related Audit and Inspection Reports',
}

TOPIC_WITH_SUBTOPICS = ['OAS', 'OE']

REPORT_URL_MAPPING = {
  "https://oig.hhs.gov/reports-and-publications/medicaid-integrity/2011/": "https://oig.hhs.gov/reports-and-publications/medicaid-integrity/2011/medicaid_integrity_reportFY11.pdf",
  "https://oig.hhs.gov/reports-and-publications/compendium/2011.asp": "https://oig.hhs.gov/publications/docs/compendium/2011/CMP-March2011-Final.pdf",
}

REPORT_PUBLISHED_MAPPING = {
  "31200010": datetime.datetime(2012, 8, 3),
  "OIG-Strategic-Plan-2014-2018": datetime.datetime(2014, 1, 1),
  "CMP-March2011-Final": datetime.datetime(2011, 3, 1),
  "hcfacreport2004": datetime.datetime(2005, 9, 1),

  # This is a published draft for next year, date taken from PDF metadata
  'FY2015_HHSOIG_Congressional_Justification': datetime.datetime(2014, 3, 4),

  # This has an incorrect datetime (2028)
  'oei-06-98-00321': datetime.datetime(2000, 12, 1),

  # This has an incorrect datetime (14-21-2010)
  '70903133': datetime.datetime(2010, 4, 21),

  # This has an incorrect datetime (03-05-2015)
  '31300031': datetime.datetime(2014, 3, 1),

  # This has an incorrect datetime (04-23-3012)
  '91102005': datetime.datetime(2012, 4, 23),
}

BLACKLIST_TITLES = [
  'Return to Reports and Publications',
  'Read the Summary',
  'Back to Archives',
  'Top',
]

# These are links that appear like reports, but are not.
BLACKLIST_REPORT_URLS = [
  'http://get.adobe.com/reader/',

  # See note to IG web team
  'https://oig.hhs.gov/reports/region3/30700500.htm',
  'https://oig.hhs.gov/oas/reports/region5/50800067.asp',
]

BASE_URL = "https://oig.hhs.gov"

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    extract_reports_for_topic(topic, year_range)
    if topic in TOPIC_TO_ARCHIVE_URL:
      extract_reports_for_topic(topic, year_range, archives=True)

def extract_reports_for_topic(topic, year_range, archives=False):
  topic_url = TOPIC_TO_ARCHIVE_URL[topic] if archives else TOPIC_TO_URL[topic]

  if topic in TOPIC_WITH_SUBTOPICS:
    subtopic_map = get_subtopic_map(topic_url)
  else:
    subtopic_map = {None: topic_url}

  topic_name = TOPIC_NAMES[topic]
  for subtopic_name, subtopic_url in subtopic_map.items():
    logging.debug("## Processing subtopic %s" % subtopic_name)
    extract_reports_for_subtopic(subtopic_url, year_range, topic_name, subtopic_name)

def extract_reports_for_subtopic(subtopic_url, year_range, topic_name, subtopic_name):
  doc = beautifulsoup_from_url(subtopic_url)
  if not doc:
    raise Exception("Failure fetching subtopic URL: %s" % subtopic_url)

  results = None

  # This URL is different than the rest and needs to find the "p > a"s first.
  if subtopic_url == TOPIC_TO_URL['TMPC']:
    results = doc.select("#leftContentInterior > p > a")
  if not results:
    results = doc.select("#leftContentInterior dl dd")
  if not results:
    results = doc.select("#leftContentInterior ul li")
  if not results:
    results = doc.select("#leftContentInterior > p > a")
  for result in results:
    if 'crossref' in result.parent.parent.attrs.get('class', []):
      continue
    if result.parent.parent.attrs.get('id') == 'related':
      continue
    report = report_from(result, year_range, topic_name, subtopic_url, subtopic_name)
    if report:
      inspector.save_report(report)

def report_from(result, year_range, topic, subtopic_url, subtopic=None):
  # Ignore links to other subsections
  if result.get('class') and result['class'][0] == 'crossref':
    return

  if result.name == 'a':
    # Sometimes we already have a link
    result_link = result
  else:
    result_link = result.find("a")

  # No link found, this is probably just an extra <li> on the page.
  if result_link is None:
    return

  # If this is just a anchor link on the same page, skip
  if not strip_url_fragment(result_link['href']):
    return

  report_url = urljoin(subtopic_url, result_link['href']).strip()

  if report_url in REPORT_URL_MAPPING:
    report_url = REPORT_URL_MAPPING[report_url]

  # Ignore reports from other sites
  if BASE_URL not in report_url:
    return

  if report_url in BLACKLIST_REPORT_URLS:
    return

  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  title = result_link.text.strip()
  if title in BLACKLIST_TITLES:
    return

  # Try a quick check from the listing page to see if we can bail out based on
  # the year
  try:
    published_on_text = result.find_previous("dt").text.strip()
    published_on = datetime.datetime.strptime(published_on_text, "%m-%d-%Y")
  except (AttributeError, ValueError):
    published_on = None

  if published_on and published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    # Process reports with landing pages
    if extension.lower() != '.pdf':
      report_url, published_on = report_from_landing_url(report_url)
    else:
      published_on = published_on_from_inline_link(
        result,
        report_filename,
        title,
        report_id,
        report_url,
      )

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  result = {
    'inspector': 'hhs',
    'inspector_url': 'https://oig.hhs.gov',
    'agency': 'hhs',
    'agency_name': 'Health & Human Services',
    'report_id': report_id,
    'topic': topic.strip(),
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if subtopic:
    result['subtopic'] = subtopic
  return result

def report_from_landing_url(report_url):
  doc = beautifulsoup_from_url(report_url)
  if not doc:
    raise Exception("Failure fetching report landing URL: %s" % report_url)

  possible_tags = (
    doc.select("h1") +
    doc.select("h2") +
    doc.select("h3") +
    doc.select("body font p b") +
    doc.select("body center") +
    doc.select("body blockquote p")
  )
  for possible_tag in possible_tags:
    published_on = get_published_date_from_tag(possible_tag)
    if published_on:
      break

  try:
    relative_url = doc.select("#leftContentInterior p.download a")[0]['href']
  except IndexError:
    try:
      relative_url = doc.select("#leftContentInterior p a")[0]['href']
    except IndexError:
      relative_url = None

  if relative_url is not None:
    report_url = urljoin(report_url, relative_url)
  return report_url, published_on

def clean_published_text(published_text):
  return published_text.strip().replace(" ", "").replace("\xa0", "")

def get_published_date_from_tag(possible_tag):
  try:
    published_on_text = possible_tag.contents[0].split("|")[0]
  except (TypeError, IndexError):
    published_on_text = possible_tag.text

  published_on_text = clean_published_text(published_on_text)

  date_formats = [
    '%m-%d-%Y',
    '%m-%d-%y',
    '%b%d,%Y',
    '%B%d,%Y',
    '%B,%d,%Y',
    '%B%Y',
  ]
  for date_format in date_formats:
    try:
      return datetime.datetime.strptime(published_on_text, date_format)
    except ValueError:
      pass

  for date_format in date_formats:
    try:
      published_text = clean_published_text(possible_tag.contents[-1])
      return datetime.datetime.strptime(published_text, date_format)
    except (ValueError, TypeError, IndexError):
      pass

def published_on_from_inline_link(result, report_filename, title, report_id, report_url):
  try:
    published_on_text = result.find_previous("dt").text.strip()
    published_on = datetime.datetime.strptime(published_on_text, "%m-%d-%Y")
  except (ValueError, AttributeError):
    try:
      cite_text = result.find_next("cite").text
      if ';' in cite_text:
        published_on_text = cite_text.split(";")[-1].rstrip(")")
      elif ':' in cite_text:
        published_on_text = cite_text.split(":")[-1].rstrip(")")
      else:
        published_on_text = cite_text.split(",")[-1].rstrip(")")
      published_on = datetime.datetime.strptime(published_on_text.strip(), '%m/%y')
    except (AttributeError, ValueError):
      try:
        fiscal_year = int(result.text.split(":")[0].split()[1])
        published_on = datetime.datetime(fiscal_year - 1, 10, 1)
      except (ValueError, IndexError):
        try:
          fiscal_year = int(report_filename.split("-")[0])
          published_on = datetime.datetime(fiscal_year - 1, 10, 1)
        except ValueError:
          try:
            published_on = datetime.datetime.strptime(title.replace(": ", ":"), "Compendium:%B %Y Edition")
          except ValueError:
            try:
              published_on = datetime.datetime.strptime(report_id.split("-")[-1], "%m%d%Y")
            except ValueError:
              try:
                report_year = int(report_url.split("/")[-2:-1][0])
                published_on = datetime.datetime(report_year, 1, 1)
              except (ValueError, IndexError):
                try:
                  fiscal_year = int(title.replace("Fiscal Year ", ""))
                  published_on = datetime.datetime(fiscal_year - 1, 10, 1)
                except ValueError:
                  # Try using the last-modified header
                  response = utils.scraper.request(method='HEAD', url=report_url)
                  last_modified = response.headers['Last-Modified']
                  published_on = datetime.datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
                  if published_on.year < 2003:
                    # We don't trust the last-modified for dates before 2003
                    # since a lot of historical reports were published at this
                    # time. For these reports, fallback to a hacky method based
                    # on the report id. For example: oei-04-12-00490. These are
                    # the dates that the report_id was assigned which is before
                    # the report was actually published
                    published_on_text = "-".join(report_id.split("-")[1:3])
                    try:
                      published_on = datetime.datetime.strptime(published_on_text, '%m-%y')
                    except ValueError:
                      pass
                      # Fall back to the Last-Modified header
  return published_on

def get_subtopic_map(topic_url):
  body = utils.download(topic_url)
  doc = BeautifulSoup(body)

  subtopic_map = {}
  for link in doc.select("#leftContentInterior li a"):
    absolute_url = urljoin(topic_url, link['href'])
    absolute_url = strip_url_fragment(absolute_url)

    # Only add new URLs
    if absolute_url not in subtopic_map.values():
      subtopic_map[link.text] = absolute_url

  return subtopic_map

def beautifulsoup_from_url(url):
  body = utils.download(url)
  if body is None: return None

  doc = BeautifulSoup(body)

  # Some of the pages will return meta refreshes
  if doc.find("meta") and doc.find("meta").attrs.get('http-equiv') == 'REFRESH':
    redirect_url = urljoin(url, doc.find("meta").attrs['content'].split("url=")[1])
    return beautifulsoup_from_url(redirect_url)
  else:
    return doc

def strip_url_fragment(url):
  scheme, netloc, path, params, query, fragment = urlparse(url)
  return urlunparse((scheme, netloc, path, params, query, ""))

utils.run(run) if (__name__ == "__main__") else None
