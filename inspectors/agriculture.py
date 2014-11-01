#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector


# http://www.usda.gov/oig/rptsaudits.htm
archive = 1978

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Some reports have links with a '.PDF' extension, but they can only be
# accessed using a '.pdf' extension. There is a 404 otherwise. The
# `LOWER_PDF_REPORT_IDS` constant contains a list of the report ids that this
# applies to.
# - The link to the congressional testimony statement from 2/26/2003 should
# point to http://www.usda.gov/oig/webdocs/Testimonybudgt-2004.pdf, not
# http://www.usda.gov/oig/webdocs/IGtestimony110302.pdf

SEMIANNUAL_REPORTS_URL = "http://www.usda.gov/oig/rptssarc.htm"
AGENCY_BASE_URL = "http://www.usda.gov/oig/"
TESTIMONIES_URL = "http://www.usda.gov/oig/rptsigtranscripts.htm"
INVESTIGATION_URLS = "http://www.usda.gov/oig/newinv.htm"

OTHER_REPORT_TYPES = {
  "investigation": INVESTIGATION_URLS,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "testimony": TESTIMONIES_URL,
}

AGENCY_URLS = {
  "AARC": "rptsauditsaarc.htm",
  "AMS": "rptsauditsams.htm",
  "APHIS": "rptsauditsaphis.htm",
  "ARS": "rptsauditsars.htm",
  "CR": "rptsauditscr.htm",
  "CCC": "rptsauditsccc.htm",
  "CSRE": "rptsauditscsrees.htm",
  "FSA": "rptsauditsfsa.htm",
  "FNS": "rptsauditsfns.htm",
  "FSIS": "rptsauditsfsis.htm",
  "FAS": "rptsauditsfas.htm",
  "FS": "rptsauditsfs.htm",
  "GIPSA": "rptsauditsgipsa.htm",
  "NASS": "rptsauditsnass.htm",
  "NIFA": "rptsauditsnifa.htm",
  "NRCS": "rptsauditsnrcs.htm",
  "REE": "rptsauditsree.htm",
  "RMA": "rptsauditsrma.htm",
  "RBS": "rptsauditsrbs.htm",
  "RBEG": "rptsauditsrbeg.htm",
  "RD": "rptsauditsrd.htm",
  "RHS": "rptsauditsrhs.htm",
  "RUS": "rptsauditsrus.htm",
  "USDA": "rptsauditsmulti.htm",
}
AGENCY_NAMES = {
  "AARC": "Alternative Agricultural Research & Comm. Center",
  "AMS": "Agricultural Marketing Service",
  "APHIS": "Animal Plant Health Inspection Service",
  "ARS": "Agricultural Research Service",
  "CR": "Civil Rights",
  "CCC": "Commodity Credit Corporation",
  "CSRE": "Cooperative State Research, Ed. & Extension Service",
  "FSA": "Farm Service Agency",
  "FNS": "Food and Nutrition Service",
  "FSIS": "Food Safety and Inspection Service",
  "FAS": "Foreign Agricultural Service",
  "FS": "Forest Service",
  "GIPSA": "Grain Inspection, Packers and Stockyards Administration",
  "NASS": "National Agricultural Statistics Service",
  "NIFA": "National Institute of Food and Agriculture",
  "NRCS": "Natural Resources Conservation Service",
  "REE": "Research, Education, and Economics",
  "RMA": "Risk Management Agency",
  "RBS": "Rural Business-Cooperative Service",
  "RBEG": "Rural Business Enterprise Grant",
  "RD": "Rural Development",
  "RHS": "Rural Housing Service",
  "RUS": "Rural Utilities Service",
  "USDA": "USDA (Multi-Agency)",
}

REPORT_PUBLISHED_MAPPING = {
  "TestimonyBlurb2": datetime.datetime(2004, 7, 14),
}

# These reports have links that end with a '.PDF' extension, but must can only
# be accessed using a '.pdf' extension.
LOWER_PDF_REPORT_IDS = [
  "sarc1978_2_Part_1",
  "sarc1979_2",
  "sarc1980_2",
  "sarc1981_2",
  "sarc1982_2",
  "sarc1983_2",
  "sarc1984_2",
  "sarc1985_2",
  "sarc1986_2",
  "sarc1987_2",
  "sarc1988_2",
  "sarc1989_2",
  "sarc1990_2",
  "sarc1991_2",
  "sarc1992_2",
  "sarc1993_2",
  "sarc1994_2",
  "sarc1995_2",
  "sarc1996_2",
  "sarc1997_2",
]

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  all_audit_reports = {}
  for agency_slug, agency_path in AGENCY_URLS.items():
    agency_url = urljoin(AGENCY_BASE_URL, agency_path)
    doc = beautifulsoup_from_url(agency_url)
    results = doc.select("ul li")
    for result in results:
      report = report_from(result, agency_url, year_range,
        report_type='audit', agency_slug=agency_slug)
      if report:
        report_id = report["report_id"]
        title = report["title"]
        key = (report_id, title)
        if key in all_audit_reports:
          all_audit_reports[key]["agency"] = all_audit_reports[key]["agency"] \
                + ", " + agency_slug.lower()
        else:
          all_audit_reports[key] = report

  for report in all_audit_reports.values():
    inspector.save_report(report)

  for report_type, url in OTHER_REPORT_TYPES.items():
    doc = beautifulsoup_from_url(url)
    results = doc.select("ul li")
    for result in results:
      report = report_from(result, url, year_range, report_type=report_type)
      if report:
        inspector.save_report(report)

def report_from(result, page_url, year_range, report_type, agency_slug="agriculture"):
  try:
    # Try to find the link with text first. Sometimes there are hidden links
    # (no text) that we want to ignore.
    link = result.find_all("a", text=True)[0]
  except IndexError:
    link = result.find_all("a")[0]
  report_url = urljoin(page_url, link.get('href').strip())

  title = link.text.strip()
  if title.endswith("(PDF)"):
    title = title[:-5]
  if title.endswith("(PDF), (Report No: 30601-01-HY, Size: 847,872 bytes)"):
    title = title[:-52]
  title = title.rstrip(" ")
  title = title.replace("..", ".")
  title = title.replace("  ", " ")
  title = title.replace("REcovery", "Recovery")

  # These entries on the IG page have the wrong URLs associated with them. The
  # correct URLs were retrieved from an earlier version of the page, via the
  # Internet Archive Wayback Machine.
  if report_url == "http://www.usda.gov/oig/webdocs/IGtestimony110302.pdf" and \
      title == "Statement Of Phyllis K. Fong Inspector General: Before The " \
      "House Appropriations Subcommittee On Agriculture, Rural Development, " \
      "Food And Drug Administration And Related Agencies":
    report_url = "http://www.usda.gov/oig/webdocs/Testimonybudgt-2004.pdf"
  elif report_url == "http://www.usda.gov/oig/webdocs/Ebt.PDF" and \
      title == "Statement Of Roger C. Viadero: Before The U.S. House Of " \
      "Representatives Committee On Agriculture Subcommittee On Department " \
      "Operations, Oversight, Nutrition, And Forestry on the Urban Resources " \
      "Partnership Program":
    report_url = "http://www.usda.gov/oig/webdocs/URP-Testimony.PDF"
  elif report_url == "http://www.usda.gov/oig/webdocs/foodaidasst.PDF" and \
      title == "Testimony Of Roger C. Viadero: Before The United States " \
      "Senate Committee On Agriculture, Nutrition, And Forestry On The " \
      "Department's Processing Of Civil Rights Complaints":
    report_url = "http://www.usda.gov/oig/webdocs/IGstestimony.PDF"

  # This report is listed twice on the same page with slightly different titles
  if title == "Animal and Plant Health Inspection Service Transition and " \
      "Coordination of Border Inspection Activities Between USDA and DHS":
    return

  report_filename = report_url.split("/")[-1]
  report_id = os.path.splitext(report_filename)[0]

  # These are just summary versions of other reports. Skip for now.
  if '508 Compliant Version' in title:
    return

  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  else:
    try:
      # This is for the investigation reports
      published_on = datetime.datetime.strptime(result.text.strip(), '%B %Y (PDF)')
      title = "Investigation Bulletins {}".format(result.text.strip())
    except ValueError:
      published_on_text = result.text.split()[0].strip()

      date_formats = ['%m/%d/%Y', '%m/%Y']
      for date_format in date_formats:
        try:
          published_on = datetime.datetime.strptime(published_on_text, date_format)
        except ValueError:
          pass

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  if report_id in LOWER_PDF_REPORT_IDS:
    report_url = ".".join([report_url.rsplit(".", 1)[0], 'pdf'])

  report = {
    'inspector': 'agriculture',
    'inspector_url': 'http://www.usda.gov/oig/',
    'agency': agency_slug.lower(),
    'agency_name': AGENCY_NAMES.get(agency_slug, 'Department of Agriculture'),
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': report_type,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def beautifulsoup_from_url(url):
  body = utils.download(url)
  return BeautifulSoup(body)


utils.run(run) if (__name__ == "__main__") else None
