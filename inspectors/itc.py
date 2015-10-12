#!/usr/bin/env python

import datetime
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.usitc.gov/oig/
archive = 1990

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - None of the audit reports have dates in the visible metadata!
# - There are some typos in report numbers and link URLS for audit reports
#   between 1999 and 2001. See the comments in report_from() for details.

AUDIT_REPORTS_URL = "http://www.usitc.gov/oig/audit_reports.html"
SEMIANNUAL_REPORTS_URL = "http://www.usitc.gov/oig/semiannual_reports.htm"
PEER_REVIEWS_URL = "http://www.usitc.gov/oig/peer_reviews.htm"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  # "semiannual_report": SEMIANNUAL_REPORTS_URL,
  # "peer_review": PEER_REVIEWS_URL,
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  doc = BeautifulSoup(utils.download(AUDIT_REPORTS_URL))

  headers = doc.select("p.Ptitle1")
  if not headers:
    raise inspector.NoReportsFoundError("ITC")

  for header in headers:
    year = int(header.text.strip())
    results = header.findNextSibling("ul").select("li")

    for result in results:
      if not inspector.sanitize(result.text):
        logging.debug("Skipping empty list item.")
        continue

      report = audit_report_from(year, result, AUDIT_REPORTS_URL, year_range)
      if report:
        inspector.save_report(report)

global flag_inspection_report_01_01
flag_inspection_report_01_01 = False

def audit_report_from(year, result, landing_url, year_range):
  link = result.find("a", text=True)
  report_url = urljoin(landing_url, link.get('href'))
  report_id = "-".join(link.text.split()).replace(':', '')
  result_text = [x for x in result.stripped_strings]
  title = " ".join(result_text[0].split())
  unreleased = False

  # Some reports have the wrong link and/or number listed on the website
  if report_id == "Inspection-Report-03-99" and \
        title.find("Evaluation of the Commission's Passport System's " \
        "Security") != -1:
    # The title doesn't match the ID or URL, and this title doesn't show up
    # anywhere else, so patch in the correct ID/URL and save the report.
    report_id = "Inspection-Report-01-99"
    report_url = "http://www.usitc.gov/oig/documents/OIG-IR-01-99.pdf"
  elif report_id == "Inspection-Report-02-00" and \
        title.find("Second Follow-up Review of Commission's Preparation for " \
        "Year 2000") != -1:
    # The title doesn't match the ID or URL, but the ID/URL is listed with the
    # correct title elsewhere, and the title is listed with the correct ID/URL
    # elsewhere, so we can discard this result.
    return
  elif report_id == "Inspection-Report-01-01" and \
        title.find("Self-Assessment of the Commission's Human Capital") != -1:
    # There are two identical links for the same report, keep track and
    # discard the second one. Normally this would be achieved by discarding all
    # duplicate links, but given the other link/text mismatches, it would be
    # best to address this as a special case, in case there are similar typos
    # in the future.
    global flag_inspection_report_01_01
    if flag_inspection_report_01_01:
      return
    else:
      flag_inspection_report_01_01 = True
  elif report_id == "Inspection-Report-02-01" and \
        title.find("Assessment of the Commission's Family-Friendly Programs") != -1:
    # The report ID and URL for this assessment are wrong, so we will mark it
    # as unreleased.
    report_id = "family-friendly-programs"
    report_url = None
    unreleased = True
    landing_url = AUDIT_REPORTS_URL

  estimated_date = False
  try:
    published_on_text = title.split("(")[0].strip()
    published_on = datetime.datetime.strptime(published_on_text, '%B %Y')
  except ValueError:
    # For reports where we can only find the year, set them to Nov 1st of that year
    estimated_date = True
    try:
      published_on_year = int(result.find_previous("p").text)
    except ValueError:
      published_on_year = int(title.split(":")[0])
    published_on = datetime.datetime(published_on_year, 11, 1)

  if landing_url == SEMIANNUAL_REPORTS_URL and link.text.find("-") == -1:
    # Need to add a date to some semiannual report IDs
    report_id = "%s-%s" % (report_id, published_on.strftime("%m-%y"))

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'itc',
    'inspector_url': 'http://www.usitc.gov/oig/',
    'agency': 'itc',
    'agency_name': 'International Trade Commission',
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  if unreleased:
    report['unreleased'] = True
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
