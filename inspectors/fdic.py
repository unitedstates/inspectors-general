#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# http://www.fdicoig.gov
archive = 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - The search engine has a bad PDF link for "FDIC Office of Inspector General's
#   Semiannual Report to the Congress 4/1/2003 - 9/30/2003", while reports.shtml
#   doesn't
# - Similarly, the search engine's entry for the 4/1/2009-9/30/2009 report
#   points to the wrong file, while reports.shtml has the right one
# - The press release "pr-08-24-12a.shtml" is posted twice, once with the wrong
#   title

REPORTS_URL = "http://www.fdicoig.gov/Search-Engine.asp"

# Reports with this URL should be designated as missing
GENERIC_MISSING_REPORT_URL = 'http://www.fdicoig.gov/notice.pdf'

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  doc = utils.beautifulsoup_from_url(REPORTS_URL)
  results = doc.find("table", {"cellpadding": "5"}).select("tr")
  if not results:
    raise inspector.NoReportsFoundError("FDIC")
  for index, result in enumerate(results):
    if index < 3 or not result.text.strip():
      # The first three rows are headers
      continue
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def type_for_report(text):
  if text == 'audit report':
    return 'audit'
  elif text == 'Semiannual Report to the Congress':
    return 'semiannual_report'
  elif 'Peer Review' in text:
    return 'peer_review'
  elif text in ['evaluation report', 'MLR', 'IR', 'In-Depth Review']:  # Material loss review
    return 'inspection'
  elif text == 'testimony':
    return 'testimony'
  elif 'Management and Performance Challenges' in text:
    return 'performance'
  elif 'press' in text:
    return 'press'
  else:
    return "other"

def report_from(result, year_range):
  title = result.find("em").text.strip()
  landing_url = REPORTS_URL

  hrefs = [a.get("href").strip() for a in result.find_all("a")]
  hrefs = [href for href in hrefs if href]
  if hrefs:
    unreleased = False
    report_url = urljoin(REPORTS_URL, hrefs[-1])
  else:
    unreleased = True
    report_url = None

  if report_url == "http://www.fdicoig.gov/semi-reports/sar2003mar/" \
        "oigsemi-03-09.pdf":
    # This URL is a typo, results in 404
    report_url = "http://www.fdicoig.gov/semi-reports/Semi2003OCT/sarOCT03.shtml"

  if report_url == "http://www.fdicoig.gov/semi-reports/sar2009mar/" \
        "oigsemi-03-09.pdf" and \
        title == "FDIC Office of Inspector General's Semiannual Report to " \
        "the Congress 4/1/2009 - 9/30/2009":
    # This URL points to the wrong report
    report_url = "http://www.fdicoig.gov/semi-reports/SAROCT09/" \
        "OIGSemi_FDIC_09-9-09.pdf"

  if report_url == "http://www.fdicoig.gov/press/pr-08-24-12.shtml" and \
        title == "Bank President Imprisoned for Embezzlement":
    # The title and URL don't match, and both were copied from other reports,
    # so we skip this entry
    return None

  if report_url and report_url != GENERIC_MISSING_REPORT_URL:
    report_filename = report_url.split("/")[-1]
    report_id, extension = os.path.splitext(report_filename)
    if report_url.find("/evaluations/") != -1:
      if not report_url.endswith("e"):
        report_id = report_id + "e"
  else:
    report_id = "-".join(title.split())[:50]
    report_id = report_id.replace(":", "")

  published_on_text = result.select("td")[2].text
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
  except ValueError:
    logging.debug("[%s] Skipping since all real reports have published dates and this does not" % report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report_type_text = result.select("td")[0].text
  report_type = type_for_report(report_type_text)

  missing = False
  if report_url == GENERIC_MISSING_REPORT_URL:
    missing = True
    unreleased = True
    report_url = None

  report = {
    'inspector': "fdic",
    'inspector_url': "http://www.fdicoig.gov",
    'agency': "fdic",
    'agency_name': "Federal Deposit Insurance Corporation",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  if missing:
    report['missing'] = missing
  return report

utils.run(run) if (__name__ == "__main__") else None
