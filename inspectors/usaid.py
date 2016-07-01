#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://oig.usaid.gov
archive = 1998

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - The report https://oig.usaid.gov/content/mcc-oig-semiannual-report-congress-april-1-2005-september-31-2005
# is listed as going through September 31, 2005, but September only has 30 days.
# - Some reports have had the wrong files uploaded, see MISMATCHED_REPORT_URLS

AUDIT_REPORTS_URL = "https://oig.usaid.gov/auditandspecialbyyear?page={page}"
TESTIMONY_URL = "https://oig.usaid.gov/testimony?page={page}"
SEMIANNUAL_REPORTS_URL = "https://oig.usaid.gov/reports/semi-annual"

PAGINATED_REPORT_FORMATS = [
  ("testimony", TESTIMONY_URL),
  ("audit", AUDIT_REPORTS_URL),
]

DATE_RE = re.compile("(:?January|February|March|April|May|June|July|"
                     "August|September|October|November|December) [0-9]{2}, "
                     "[0-9]{4}")

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports with pagination
  for report_type, report_url_format in PAGINATED_REPORT_FORMATS:
    for page in range(0, 999):
      url = report_url_format.format(page=page)
      doc = utils.beautifulsoup_from_url(url)
      results = doc.select("li.views-row")
      if not results:
        if page == 0:
          raise inspector.NoReportsFoundError("USAID (%s)" % report_type)
        else:
          break

      for result in results:
        report = report_from(result, url, report_type, year_range)
        if report:
          inspector.save_report(report)

  # Pull the semiannual reports (no pagination)
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("li.views-row")
  if not results:
    raise inspector.NoReportsFoundError("USAID (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

MISMATCHED_REPORT_URLS = (
  "https://oig.usaid.gov/sites/default/files/audit-reports/1-522-02-013-p.pdf",
  "https://oig.usaid.gov/sites/default/files/audit-reports/7-641-03-002-p.pdf",
  "https://oig.usaid.gov/sites/default/files/audit-reports/b-118-05-002-p_0.pdf"
)

def report_from(result, landing_url, report_type, year_range):
  link = result.find("a")

  if link:
    title = link.text
    report_url = link.get('href')
    unreleased = False
  else:
    title = result.select("div.views-field-title")[0].text
    report_url = None
    unreleased = True

  published_on = None
  try:
    published_on_text = result.select("span.date-display-single")[0].text
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
  except IndexError:
    pass
  if not published_on:
    try:
      title_text = result.select("div.views-field-title span")[0].text.strip()
      date_match = DATE_RE.match(title_text)
      published_on_text = date_match.group(0)
      published_on = datetime.datetime.strptime(published_on_text, "%B %d, %Y")
      title = title_text[date_match.end():]
    except (IndexError, AttributeError):
      pass

  if not published_on:
    admin.log_no_date("usaid", report_url, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  try:
    report_id_text = result.select("div.views-field-field-auditreport-doc-data")[0].text.strip()
    report_id = "-".join(report_id_text.replace("/", "-").replace(":", "").split())
  except IndexError:
    report_id = None

  if not report_id and report_url:
    report_filename = report_url.split("/")[-1]
    report_id, _ = os.path.splitext(report_filename)

  if not report_id:
    report_id = "{}-{}".format("-".join(title.split()), published_on_text)

  report_id = report_id.replace("/", "-")

  if title.startswith("Follow-Up"):
    report_id = report_id + "-follow-up"

  if report_url == "https://oig.usaid.gov/sites/default/files/audit-reports/" \
        "0-000-12-001-s_0.pdf":
    # Two versions of this report have been uploaded
    report_id = report_id + "_final"

  if report_url == "https://oig.usaid.gov/sites/default/files/audit-reports/" \
        "1-520-01-010-p_0.pdf":
    # This file has been uploaded twice, once with "_0" and once without
    return None

  if report_url in MISMATCHED_REPORT_URLS:
    # The report number and PDF file for these reports are copies of unrelated
    # reports
    report_id = "-".join(re.split("[^a-z]+", title.lower()))
    report_url = None
    unreleased = True

  report = {
    'inspector': "usaid",
    'inspector_url': "https://oig.usaid.gov",
    'agency': "usaid",
    'agency_name': "Agency For International Development",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
    del report['url']
  return report

def semiannual_report_from(result, year_range):
  link = result.find("a")

  title = link.text

  # Parse the report title. Ex:
  # 'OIG Semiannual Report to the Congress: October 1, 2013 - March 31, 2014 (incl. MCC)'
  published_on_text = title.split("-")[-1].split("–")[-1].split("(")[0].strip()
  published_on_text = published_on_text.replace("September 31", "September 30")  # See note to IG Web team
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  landing_url = urljoin(SEMIANNUAL_REPORTS_URL, link.get('href'))
  landing_page = utils.beautifulsoup_from_url(landing_url)

  report_url = landing_page.select("div.field-type-file a")[0].get('href')
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  report = {
    'inspector': "usaid",
    'inspector_url': "https://oig.usaid.gov",
    'agency': "usaid",
    'agency_name': "Agency For International Development",
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
