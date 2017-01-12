#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://www.fcc.gov/inspector-general
archive = 1994

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:

AUDIT_REPORTS_URL = "https://www.fcc.gov/inspector-general/reports/general/audit-inspection-and-evaluation-reports-issued-office-inspector"
SEMIANNUAL_REPORTS_URL = "https://www.fcc.gov/inspector-general/reports/general/semi-annual-reports-issued-office-inspector-general"
OTHER_REPORTS_URL = "https://www.fcc.gov/general/office-inspector-general-news-written-statements-press-releases-and-peer-review-report"

DATE_FORMATS = [
  "%m/%d/%Y",
  "%m/%d/%y",
]

RE_EXTRA_FILES = re.compile("(?:Transmittal_(?:[Ll]etter|ltr|Memo)|"
                            "CoverLetter|"
                            "Attachment)")

def run(options):
  year_range = inspector.year_range(options, archive)

  doc = utils.beautifulsoup_from_url(AUDIT_REPORTS_URL)
  results = doc.article.find_all("tr")
  if not results:
    raise inspector.NoReportsFoundError("FCC (audit reports)")
  for result in results:
    report = report_from(result, AUDIT_REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.article.find_all("tr")
  if not results:
    raise inspector.NoReportsFoundError("FCC (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, SEMIANNUAL_REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

  doc = utils.beautifulsoup_from_url(OTHER_REPORTS_URL)
  results = doc.article.find_all("p")
  if not results:
    raise inspector.NoReportsFoundError("FCC (other)")
  for result in results:
    report = other_report_from(result, OTHER_REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

def report_from(result, page_url, year_range):
  tds = result.find_all("td")
  if len(tds) == 1:
    # Title row, with colspan="3"
    return
  if len(tds) == 0:
    # Degenerate row
    return
  if tds[1]["align"] == "Center":
    # Column headers
    return
  if not result.text.strip():
    # Empty spacer row
    return

  if tds[1].p is not None:
    title = tds[1].p.contents[0]
  else:
    title = tds[1].text
  title = re.sub("\\s+", " ", title).strip()

  links = [a["href"] for a in result.find_all("a")]
  if len(links) > 1:
    links = [link for link in links if not RE_EXTRA_FILES.search(link)]
  if len(links) == 0:
    raise Exception("Couldn't find link for {!r}".format(title))
  if len(links) > 1:
    raise Exception("Found multiple links for {!r}".format(title))
  report_url = urljoin(page_url, links[0])
  report_filename = os.path.basename(report_url)
  report_id, extension = os.path.splitext(report_filename)

  published_on_text = tds[0].text.strip()
  for date_format in DATE_FORMATS:
    try:
      published_on = datetime.datetime.strptime(published_on_text, date_format)
      break
    except ValueError:
      pass
  else:
    admin.log_no_date("fcc", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fcc',
    'inspector_url': 'https://www.fcc.gov/inspector-general',
    'agency': 'fcc',
    'agency_name': "Federal Communications Commission",
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, page_url, year_range):
  tds = result.find_all("td")
  if len(tds) <= 1:
    # Title row, with colspan, or degenerate row
    return
  if tds[0]["align"] == "center":
    # Column headers
    return

  if tds[0].br:
    title = tds[0].contents[0].strip()
  else:
    title = tds[0].text.strip()
  published_on_text = title.split("to")[-1].split("through")[-1].strip()
  published_on = datetime.datetime.strptime(published_on_text, "%B %d, %Y")
  title = "Semi-Annual Report - {}".format(title)

  report_url = urljoin(page_url, result.a["href"])
  report_filename = os.path.basename(report_url)
  report_id, extension = os.path.splitext(report_filename)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fcc',
    'inspector_url': 'https://www.fcc.gov/inspector-general',
    'agency': 'fcc',
    'agency_name': "Federal Communications Commission",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def other_report_from(result, page_url, year_range):
  if result.text.strip() in ["Written Statements", "Peer Review Report", "News / Press Releases"]:
    # Headers
    return
  if not result.text.strip():
    # Empty paragrpah
    return

  if result.strong:
    title = result.strong.text.strip()
  else:
    title = result.find("span", class_="bodytextbold").text.strip()

  links = result.find_all("a")
  if len(links) > 1:
    temp = [a for a in links if "Statement" in a.previous_sibling]
    if len(temp) == 1:
      links = temp
  links = [a["href"] for a in links]
  if len(links) == 0:
    raise Exception("Couldn't find link for {!r}".format(title))
  if len(links) > 1:
    raise Exception("Found multiple links for {!r}".format(title))
  report_url = urljoin(page_url, links[0])
  report_filename = os.path.basename(report_url)
  report_id, extension = os.path.splitext(report_filename)

  if report_id == "USF_Low_Income_Indictment_040914":
    published_on = datetime.datetime(2014, 4, 9)
  else:
    try:
      published_on_text = result.find("span", class_="navlinksbody").text
      published_on = datetime.datetime.strptime(published_on_text, "%m/%d/%Y")
    except ValueError:
      published_on_text = result.find("span", class_="navlinksbody").find("span", class_="navlinksbody").text
      published_on = datetime.datetime.strptime(published_on_text, "%m/%d/%Y")

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fcc',
    'inspector_url': 'https://www.fcc.gov/inspector-general',
    'agency': 'fcc',
    'agency_name': "Federal Communications Commission",
    'type': 'other',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
