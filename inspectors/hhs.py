#!/usr/bin/env python

import datetime
import itertools
import logging
import os
import re
from urllib.parse import urljoin, urlparse, urlunparse, urldefrag

from utils import utils, inspector

# http://oig.hhs.gov/reports-and-publications/index.asp
archive = 1985

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
#  http://oig.hhs.gov/reports-and-publications/oei/a.asp
#  As a fallback, this scraper uses the HTTP Last-Modified header for reports
#  published after 2002. For reports published before 2002, we use the report id
#  month-year as an approximation of the published date.
#  - Fix published date for http://oig.hhs.gov/oas/reports/region3/31200010.asp
#  on http://oig.hhs.gov/reports-and-publications/oas/cms.asp. It currently
#  says 08-03-2102
#  - Fix published date for http://oig.hhs.gov/oei/reports/oei-06-98-00321.pdf
#  on http://oig.hhs.gov/reports-and-publications/oei/s.asp. It currently
#  says Dec 2028.
#  - Fix published date for http://oig.hhs.gov/oas/reports/region7/70903133.asp
#  It currently says 14-21-2010.
#  - Fix published date for http://oig.hhs.gov/oas/reports/region3/31300031.asp
#  It currently says 03-05-2015.
#  - Fix published date for http://oig.hhs.gov/oas/reports/region9/91102005.asp
#  It currently says 04-23-3012.
#  - Add missing report for 'Use of Discounted Airfares by the Office of the Secretary' (A-03-07-00500)
#  linked to from http://oig.hhs.gov/reports-and-publications/oas/dept.asp
#  - The report http://oig.hhs.gov/oas/reports/region5/50800067.asp returns a 500.
#  - The link to the report for "Personnel Suitability and Security (OAI-02-86-00079; 11/87)"
#  points to a copy of the report OAI-07-86-00079.
#  - The link to the report for "Errors Resulting in Overpayment In the AFDC Program (OAI-04-86-0024; 06/87)"
#  points to a copy of the report OEI-05-90-00720.
#  - The date for OEI-07-91-01470 is incorrectly listed as 4/94 on the S page,
#  and correctly listed as 4/92 on the O page.
#  - There is a typo in one of the links on http://oig.hhs.gov/reports-and-publications/oei/h.asp,
#  it should point to #hospitals, not #hospiatls.

TOPIC_TO_URL = {
  "OAS": 'http://oig.hhs.gov/reports-and-publications/oas/index.asp',
  "OE": 'http://oig.hhs.gov/reports-and-publications/oei/subject_index.asp',
  "HCF": 'http://oig.hhs.gov/reports-and-publications/hcfac/index.asp',
  "SAR": 'http://oig.hhs.gov/reports-and-publications/semiannual/index.asp',
  "MIR": 'http://oig.hhs.gov/reports-and-publications/medicaid-integrity/index.asp',
  "TMPC": 'http://oig.hhs.gov/reports-and-publications/top-challenges/',
  "CPR": 'http://oig.hhs.gov/reports-and-publications/compendium/index.asp',
  "SP": 'http://oig.hhs.gov/reports-and-publications/strategic-plan/index.asp',
  "WP": 'http://oig.hhs.gov/reports-and-publications/workplan/index.asp',
  "POR": 'http://oig.hhs.gov/reports-and-publications/portfolio/index.asp',
  "FOIA": 'http://oig.hhs.gov/reports-and-publications/foia/index.asp',
  "FRN": 'http://oig.hhs.gov/reports-and-publications/federal-register-notices/index.asp',
  "RA": 'http://oig.hhs.gov/reports-and-publications/regulatory-authorities/index.asp',

  "B": 'http://oig.hhs.gov/reports-and-publications/budget/index.asp',
  # "RAOR": 'http://oig.hhs.gov/reports-and-publications/recovery/index.asp',
  "RAA": 'http://oig.hhs.gov/reports-and-publications/recovery/recovery_reports.asp',
}

TOPIC_TO_ARCHIVE_URL = {
  "OAS": 'http://oig.hhs.gov/reports-and-publications/archives/oas/index.asp',

  # Some reports missing published dates
  # "SAR": 'http://oig.hhs.gov/reports-and-publications/archives/semiannual/index.asp',

  # Some reports missing published dates
  # "TMPC": 'http://oig.hhs.gov/reports-and-publications/archives/top-challenges/index.asp',

  # No published dates
  # "CPR": 'http://oig.hhs.gov/reports-and-publications/archives/compendium/redbook.asp',

  # Some reports missing published dates
  # "WP": 'http://oig.hhs.gov/reports-and-publications/archives/workplan/index.asp',

  "FRN": 'http://oig.hhs.gov/reports-and-publications/archives/federal-register-notices/index.asp',
  "B": 'http://oig.hhs.gov/reports-and-publications/archives/budget/index.asp',
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
  "http://oig.hhs.gov/reports-and-publications/medicaid-integrity/2011/": "http://oig.hhs.gov/reports-and-publications/medicaid-integrity/2011/medicaid_integrity_reportFY11.pdf",
  "http://oig.hhs.gov/reports-and-publications/compendium/2011.asp": "http://oig.hhs.gov/publications/docs/compendium/2011/CMP-March2011-Final.pdf",
  "http://oig.hhs.gov/reports-and-publications/oas/reports/region3/30700500.htm": "http://oig.hhs.gov/oas/reports/region3/30700500.htm",
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

  # See OEI_COMBINED_LANDING_PAGES below, we are skipping parsing the landing
  # pages for these reports for now
  'oei-09-08-00580': datetime.datetime(2011, 9, 30),
  'oei-09-08-00581': datetime.datetime(2011, 9, 30),
  'oei-05-09-00560': datetime.datetime(2011, 8, 29),
  'oei-05-09-00561': datetime.datetime(2011, 8, 29),

  # This has the right date in one place and the wrong date in another
  'oei-07-91-01470': datetime.datetime(1992, 4, 1),

  "41206159": datetime.datetime(2013, 12, 4),
}

# This manually entered data is used to skip landing pages that hold more than
# one report. We use the correct PDF link for each, which makes deduplication
# easier.
OEI_COMBINED_LANDING_PAGES = {
  "http://oig.hhs.gov/oei/reports/oei-09-08-00580-00581.asp": {
    "Access to Mental Health Services at Indian Health Service and Tribal Facilities": "http://oig.hhs.gov/oei/reports/oei-09-08-00580.pdf",
    "Access to Kidney Dialysis Services at Indian Health Service and Tribal Facilities": "http://oig.hhs.gov/oei/reports/oei-09-08-00581.pdf"
  },
  "http://oig.hhs.gov/oei/reports/oei-05-09-00560-00561.asp": {
    "Miami Independent Diagnostic Testing Facilities' Compliance with Medicare Standards": "http://oig.hhs.gov/oei/reports/oei-05-09-00560.pdf",
    "Los Angeles Independent Diagnostic Testing Facilities' Compliance with Medicare Standards": "http://oig.hhs.gov/oei/reports/oei-05-09-00561.pdf"
  },
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
  'http://oig.hhs.gov/reports/region3/30700500.htm',
  'http://oig.hhs.gov/oas/reports/region5/50800067.asp',

  #press release, format is completely inconsistent with everything else
  'http://oig.hhs.gov/newsroom/news-releases/2014/sar14fall.asp',

  # Duplicate report, uploaded in two regions
  'http://oig.hhs.gov/oas/reports/region1/100300001.htm',

  # Summary maps for report series
  'http://oig.hhs.gov/oas/jurisdiction-map/',
  'http://oig.hhs.gov/oas/map/',
]

TITLE_NORMALIZATION = {
  "ReportingAbuses of Persons with Disabilities":
    "Reporting Abuses of Persons with Disabilities",
  "Officeof Inspector General's Partnership Plan - New York StateComptroller Report on Controlling Medicaid Paymentsfor School and Preschool Supportive Health Services":
    "Office of Inspector General's Partnership Plan - New York State Comptroller Report on Controlling Medicaid Payments for School and Preschool Supportive Health Services",
  "OIG Partnership Plan: Drug Delivery System for Montana's Medicaid Program":
    "Office of Inspector General's Partnership Plan: Drug Delivery System for Montana's Medicaid Program",
  "Partnership Audit of Medicaid Paymentsfor Oxygen Related Durable Medical Equipment and Supplies - January 1, 1998 through December 31, 2000 Kentucky Department for Medicaid Services, Frankfort, Kentucky":
    "Partnership Audit of Medicaid Payments for Oxygen Related Durable Medical Equipment and Supplies - January 1, 1998 through December 31, 2000 Kentucky Department for Medicaid Services, Frankfort, Kentucky",
  "Partnership Audit of Medicaid Paymentsfor Oxygen Related Durable Medical Equipment and Supplies - January 1, 1998 through December31, 2000 Kentucky Department for Medicaid Services, Frankfort, Kentucky":
    "Partnership Audit of Medicaid Payments for Oxygen Related Durable Medical Equipment and Supplies - January 1, 1998 through December 31, 2000 Kentucky Department for Medicaid Services, Frankfort, Kentucky",
  "OIG Partnership Plan: Medicaid Payments for Clinical Laboratory Tests in Eight States":
    "Office of Inspector General's Partnership Plan: Medicaid Payments for Clinical Laboratory Tests in Eight States",
  "OIG Partnership Plan: Montana Legislative Auditor's Office Report on Medicaid Expenditures for Durable Medical Equipment":
    "Office of Inspector General's Partnership Plan: Montana Legislative Auditor's Office Report on Medicaid Expenditures for Durable Medical Equipment",
  "OIG Partnership Plan: Transportation Services for Montana's Medicaid Program":
    "Office of Inspector General's Partnership Plan: Transportation Services for Montana's Medicaid Program",
  "Office of Inspector General's Partnership Plan-State of Montana's Medicaid Third Party Liability Program":
    "Office of Inspector General's Partnership Plan - State of Montana's Medicaid Third Party Liability Program",
  "Review of the Food and Drug Administration's Processing of a new Drug Application for Therafectin":
    "Review of the Food and Drug Administration's Processing of a New Drug Application for Therafectin",
  "OIG Partnership Plan: Medicaid Payments for Clinical Laboratory Tests in 14 States":
    "Office of Inspector General's Partnership Plan: Medicaid Payments for Clinical Laboratory Tests in 14 States",
  "OIG Partnership Plan: Review of the North Carolina Division of Medical Assistance's Reimbursement for Clinical Laboratory Services Under the Medicaid Program":
    "Office of Inspector General's Partnership Plan - Review of the North Carolina Division of Medical Assistance's Reimbursement for Clinical Laboratory Services Under the Medicaid Program",
  "Officeof Inspector General's Partnership Efforts - Texas StateAuditor's Office Report on the Department of Protectiveand Regulatory Services' Administration of Foster CareContracts":
    "Office of Inspector General's Partnership Efforts - Texas State Auditor's Office Report on the Department of Protective and Regulatory Services' Administration of Foster Care Contracts",
  "Officeof Inspector General Partnership with the State of Ohio,Office of the Auditor's Report on Review of MedicaidProvider Reimbursement Made to Crest TransportationService":
    "Office of Inspector General Partnership with the State of Ohio, Office of the Auditor's Report on Review of Medicaid Provider Reimbursement Made to Crest Transportation Service",
  "OIG Partnership Plan: Utah State Auditor's Report on Clinical Laboratory Services":
    "Office of Inspector General's Partnership Plan: Utah State Auditor's Report on Clinical Laboratory Services",
  "Auditof National Association of Families and Addiction ResearchEducation":
    "Audit of National Association of Families and Addiction Research Education (NAFARE) Chicago, Illinois - Contract No. 277-94-3009 and Grant No. UHSP08041,",
  "OIG Partnership Plan - Outpatient Claims for California's Medicaid Program":
    "Office of Inspector General's Partnership Plan: Outpatient Claims for California's Medicaid Program",
  "New York State Claimed Unallowable Community Services Block Grant Recovery Act Costs for Action for a Better Community, Inc.":
    "New York State Claimed Unallowable Community Services Block Grant Recovery Act Costs for Action for a Better Community, Inc. Audit",
  "Medicaid Program Savings Through the Use of Therapeutically Equivalent Drugs":
    "Medicaid Program Savings Through the Use of Therapeutically Equivalent Generic Drugs",
  "Results of Limited Scope Review at Instituto Socio-Economico Comunitario, Inc.":
    "Results of Limited Scope Review at Instituto Socio-Econ\xc3\xb3mico Comunitario, Inc.",
  "Results of Limited Scope Review at Accion Social de Puerto Rico, Inc.":
    "Results of Limited Scope Review at Acci\xc3\xb3n Social de Puerto Rico, Inc.",
  "Results of Limited Scope Review at the Municipality of Bayamon (Puerto Rico) Audit":
    "Results of Limited Scope Review at the Municipality of Bayam\xc3\xb3n (Puerto Rico) Audit",
  "Agriculture and Labor Program, Inc., Did Not Always Charge Allowable Costs":
    "Agriculture and Labor Program, Inc., Did Not Always Charge Allowable Costs to the Community Services Block Grant - Recovery Act Program",
}

BASE_URL = "http://oig.hhs.gov"

def run(options):
  year_range = inspector.year_range(options, archive)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = list(TOPIC_TO_URL.keys())
    topics.sort()

  for topic in topics:
    extract_reports_for_topic(topic, year_range)
    if topic in TOPIC_TO_ARCHIVE_URL:
      extract_reports_for_topic(topic, year_range, archives=True)

  deduplicate_finalize()

def extract_reports_for_topic(topic, year_range, archives=False):
  if topic == "OE":
    extract_reports_for_oei(year_range)
    return

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
  doc = utils.beautifulsoup_from_url(subtopic_url)
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
  if not results:
    raise inspector.NoReportsFoundError("HHS (%s)" % subtopic_name)
  for result in results:
    if 'crossref' in result.parent.parent.attrs.get('class', []):
      continue
    if result.parent.parent.attrs.get('id') == 'related':
      continue
    report = report_from(result, year_range, topic_name, subtopic_url, subtopic_name)
    if report:
      deduplicate_save_report(report)

def extract_reports_for_oei(year_range):
  topic_name = TOPIC_NAMES["OE"]
  topic_url = TOPIC_TO_URL["OE"]
  root_doc = utils.beautifulsoup_from_url(topic_url)

  letter_urls = set()
  for link in root_doc.select("#leftContentInterior li a"):
    absolute_url = urljoin(topic_url, link['href'])
    absolute_url = strip_url_fragment(absolute_url)
    letter_urls.add(absolute_url)

  if not letter_urls:
    raise inspector.NoReportsFoundError("HHS (OEI first pass)")

  all_results_links = {}
  all_results_unreleased = []
  for letter_url in letter_urls:
    letter_doc = utils.beautifulsoup_from_url(letter_url)

    results = letter_doc.select("#leftContentInterior ul li")
    if not results:
      raise inspector.NoReportsFoundError("HHS (OEI %s)" % letter_url)
    for result in results:
      if 'crossref' in result.parent.parent.attrs.get('class', []):
        continue
      if result.parent.parent.attrs.get('id') == 'related':
        continue

      node = result
      while node and node.name != "h2":
        node = node.previous
      if node and node.name == "h2":
        subtopic_name = str(node.text)
      else:
        subtopic_name = "(unknown)"

      links = result.findAll("a")
      if len(links) == 0:
        result.extract()
        all_results_unreleased.append([result, subtopic_name])
      else:
        link = links[0]
        url = urljoin(letter_url, link.get("href"))
        link_text = link.text

        # There are links to both the landing pages and PDF files of these
        # reports. Fix them to all use the landing pages.
        if url == "http://oig.hhs.gov/oei/reports/oei-01-08-00590.pdf":
          url = url.replace(".pdf", ".asp")
          link["href"] = url
        elif url == "http://oig.hhs.gov/oas/reports/region6/69300008.pdf":
          url = url.replace(".pdf", ".htm")
          link["href"] = url

        # See the notes at the top of this file, this is the wrong link
        if link_text == "Personnel Suitability and Security" and \
            url == "http://oig.hhs.gov/oei/reports/oai-07-86-00079.pdf":
          continue

        # These landing pages are actually for two different reports, use the
        # PDF URLs here so they don't get merged together
        if url in OEI_COMBINED_LANDING_PAGES:
          url = OEI_COMBINED_LANDING_PAGES[url][link_text]

        if url not in all_results_links:
          result.extract()
          all_results_links[url] = [result, subtopic_name]
        else:
          existing_result = all_results_links[url][0]
          for temp in result.contents:
            temp.extract()
            existing_result.append(temp)
          all_results_links[url][1] = "%s, %s" % (all_results_links[url][1], subtopic_name)

  subtopic_url = TOPIC_TO_URL["OE"]
  for result, subtopic_name in itertools.chain(all_results_links.values(), all_results_unreleased):
    report = report_from(result, year_range, topic_name, subtopic_url, subtopic_name)
    if report:
      deduplicate_save_report(report)

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

  title = result_link.text
  title = title.replace("\xe2\x80\x93", "-")
  title = inspector.sanitize(title)
  title = re.sub('\s+', ' ', title)
  if title in TITLE_NORMALIZATION:
    title = TITLE_NORMALIZATION[title]

  if title in BLACKLIST_TITLES:
    return

  report_url = urljoin(subtopic_url, result_link['href']).strip()

  if report_url in REPORT_URL_MAPPING:
    report_url = REPORT_URL_MAPPING[report_url]

  # Fix copy-paste error in link
  if (title == "Medicare Compliance Review of Altru Hospital for "
      "2012 and 2013" and
      report_url == "http://oig.hhs.gov/oas/reports/region4/41408036.asp"):
    report_url = "http://oig.hhs.gov/oas/reports/region7/71505070.asp"

  # Ignore reports from other sites
  if BASE_URL not in report_url:
    return


  if report_url in BLACKLIST_REPORT_URLS:
    return

  if report_url in OEI_COMBINED_LANDING_PAGES:
    report_url = OEI_COMBINED_LANDING_PAGES[report_url][title]

  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  if report_filename == "11302505.pdf":
    report_id = report_id + "_early_alert"


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

  # This report is listed twice, once with the wrong date
  if published_on and published_on.year == 2012 and published_on.month == 1 \
      and published_on.date == 12 and report_id == "20901002":
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

  if not published_on:
    raise inspector.NoDateFoundError(report_id, title)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  result = {
    'inspector': 'hhs',
    'inspector_url': 'http://oig.hhs.gov',
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

def filter_links(link_list, base_url):
  href_list = [element.get('href') for element in link_list]
  for i in range(len(href_list)):
    if href_list[i].startswith("http://go.usa.gov/"):
      href_list[i] = utils.resolve_redirect(href_list[i])
  href_list = [urldefrag(urljoin(base_url, href))[0] for href in href_list]
  filtered_list = [href for href in href_list \
      if href and href not in BLACKLIST_REPORT_URLS and \
      not href.startswith("mailto:")]
  filtered_list = list(set(filtered_list))
  return filtered_list

def report_from_landing_url(report_url):
  doc = utils.beautifulsoup_from_url(report_url)
  if not doc:
    raise Exception("Failure fetching report landing URL: %s" % report_url)

  # Throw away the "Related Content" box, if there is one
  related = doc.find(id="related")
  if related:
    related.extract()

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

  url_list = filter_links(doc.select("#leftContentInterior p.download a"),
                          report_url)
  if not url_list:
    url_list = filter_links(doc.select("#leftContentInterior p a"), report_url)
  if len(url_list) > 1:
    raise Exception("Found multiple links on %s:\n%s" % (report_url, url_list))
  elif len(url_list) == 1:
    report_url = url_list[0]

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
  published_on = None
  try:
    published_on_text = result.find_previous("dt").text.strip()
    published_on = datetime.datetime.strptime(published_on_text, "%m-%d-%Y")
  except (ValueError, AttributeError):
    for cite in result.find_all("cite"):
      try:
        cite_text = cite.text
        if ';' in cite_text:
          published_on_text = cite_text.split(";")[-1].rstrip(")")
        elif ':' in cite_text:
          published_on_text = cite_text.split(":")[-1].rstrip(")")
        else:
          published_on_text = cite_text.split(",")[-1].rstrip(")")
        published_on = datetime.datetime.strptime(published_on_text.strip(), '%m/%y')
        break
      except (AttributeError, ValueError):
        pass
  if published_on == None:
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
  doc = utils.beautifulsoup_from_url(topic_url)

  subtopic_map = {}
  for link in doc.select("#leftContentInterior li a"):
    absolute_url = urljoin(topic_url, link['href'])
    absolute_url = strip_url_fragment(absolute_url)

    # Only add new URLs
    if absolute_url not in subtopic_map.values():
      while link.br:
        link.br.replace_with(" ")
      subtopic_name = link.text.replace("  ", " ").strip()
      subtopic_map[subtopic_name] = absolute_url

  if not subtopic_map:
    raise inspector.NoReportsFoundError("OEI (subtopics)")

  return subtopic_map

def strip_url_fragment(url):
  scheme, netloc, path, params, query, fragment = urlparse(url)
  return urlunparse((scheme, netloc, path, params, query, ""))

_report_storage = {}
def deduplicate_save_report(report):
  global _report_storage
  key = (report['title'], report['url'], report['published_on'])
  if key in _report_storage:
    if report['topic'] not in _report_storage[key]['topic']:
      _report_storage[key]['topic'] = _report_storage[key]['topic'] + ", " + \
          report['topic']
    if report.get('subtopic'):
      if _report_storage[key].get('subtopic'):
        if report['subtopic'] not in _report_storage[key]['subtopic']:
          _report_storage[key]['subtopic'] = _report_storage[key]['subtopic'] \
              + ", " + report['subtopic']
      else:
        _report_storage[key]['subtopic'] = report['subtopic']
  else:
    _report_storage[key] = report

def deduplicate_finalize():
  global _report_storage
  for report in _report_storage.values():
    inspector.save_report(report)
  _report_storage = {}

utils.run(run) if (__name__ == "__main__") else None
