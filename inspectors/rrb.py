#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://www.rrb.gov/OurAgency/InspectorGeneral
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "https://www.rrb.gov/OurAgency/InspectorGeneral/Library?field_report_title_value={}&page={}"
REPORT_TYPES = [
  ("semiannual_report", "OIG Semiannual Reports"),
  ("audit", "OIG Audit Reports"),
  ("other", "OIG Strategic Plan"),
  ("other", "OIG Special Reports"),
  ("other", "OIG Budgetary Documents"),
  ("other", "OIG Commercial Activities Report"),
  ("peer_review", "OIG Office of Audit Peer Reviews"),
  ("other", "OIG American Recovery and Reinvestment Act"),
]
DATE_RE = re.compile("Report Date: ([0-9]{2}/[0-9]{2}/[0-9]{4})")
SAR_RE = re.compile("Semiannual Report - ([A-Z][a-z]+ [0-9]{4})")
IE_DOWNLOAD_SUFFIX_RE = re.compile("%5B[0-9]+%5D")

REPORT_ID_PUBLISHED_MAP = {
  # Peer reviews
  "2015_03": datetime.datetime(2015, 9, 23),
  "2012_03": datetime.datetime(2012, 11, 21),
  "2009_03": datetime.datetime(2009, 8, 24),
  "2006_03": datetime.datetime(2006, 9, 25),
  "2003_03": datetime.datetime(2003, 12, 10),

  "OpenAuditRecommendations": datetime.datetime(2017, 3, 31),
  "strategic_plan_2016-2020": datetime.datetime(2015, 9, 30),
  "FY2017BudgetSub": datetime.datetime(2015, 9, 9),
  "2017_senate": datetime.datetime(2016, 2, 5),
  "FY2018BudgetJustification": datetime.datetime(2017, 5, 17),
  "OIGFY2019budgetsubmission": datetime.datetime(2017, 9, 8),
  "FY2006InventoryReport": datetime.datetime(2007, 8, 14),
  "2007_Inv_Rprt": datetime.datetime(2009, 7, 13),
  "2008_Inv_Rprt": datetime.datetime(2009, 7, 13),
  "2009_Inv_Rprt": datetime.datetime(2009, 7, 13),
  "oig_oversight_plan": datetime.datetime(2009, 3, 6),
}

REPORT_TITLE_PUBLISHED_MAP = {
  "Audit of Controls to Safeguard Sensitive Personally Identifiable Information": datetime.datetime(2007, 1, 1),
  "Review of Access Controls in the End-User Computing General Support System": datetime.datetime(2005, 1, 1),
  "External Quality Assurance Review of the Corporation for National Service, Office of Inspector General": datetime.datetime(2001, 1, 1),
  "Security Controls Analysis for the Office of Inspector General": datetime.datetime(2001, 1, 1),
  "Site Security Assessment for the Office of Inspector General": datetime.datetime(2001, 1, 1),
}


def run(options):
  year_range = inspector.year_range(options, archive)

  for report_type, report_title_key in REPORT_TYPES:
    page = 0
    while True:
      url = REPORTS_URL.format(report_title_key, page)
      doc = utils.beautifulsoup_from_url(url)
      results = doc.select(".view-content table tbody tr")
      if not results:
        raise inspector.NoReportsFoundError("RRB")
      for result in results:
        report = report_from(result, url, report_type, year_range)
        if report:
          inspector.save_report(report)
      if doc.select(".pager__item--next"):
        page += 1
      else:
        break


def report_from(result, landing_url, report_type, year_range):
  td = result.select("td")[1]
  link = td.a

  if link:
    title = re.sub("\\s+", " ", link.text.strip())
    unreleased = False
    report_url = urljoin(landing_url, link.get('href'))
    report_filename = report_url.split("/")[-1]
    report_filename = IE_DOWNLOAD_SUFFIX_RE.sub("", report_filename)
    report_id, _ = os.path.splitext(report_filename)
  else:
    title = re.sub("\\s+", " ", td.text.strip())
    title = title.replace(" (Unavailable)", "")
    unreleased = True
    report_url = None

  published_on = None
  published_on_match = DATE_RE.search(td.text)
  if published_on_match:
    published_on_text = published_on_match.group(1)
    published_on = datetime.datetime.strptime(published_on_text, "%m/%d/%Y")

  if published_on is None and link is not None:
    sar_match = SAR_RE.search(link.text)
    if sar_match:
      published_on = datetime.datetime.strptime(sar_match.group(1), "%B %Y")
    else:
      if report_id in REPORT_ID_PUBLISHED_MAP:
        published_on = REPORT_ID_PUBLISHED_MAP[report_id]

  if link is None and published_on is None:
    if title in REPORT_TITLE_PUBLISHED_MAP:
      published_on = REPORT_TITLE_PUBLISHED_MAP[title]
    else:
      admin.log_no_date("rrb", "?", title)
      return

  if link is None:
    report_id = "{}-{}".format(published_on.strftime("%m-%d-%y"), "-".join(title.split()))[:50]

  if published_on is None:
    admin.log_no_date("rrb", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % title)
    return

  report = {
    'inspector': 'rrb',
    'inspector_url': "http://www.rrb.gov/oig/",
    'agency': 'rrb',
    'agency_name': "Railroad Retirement Board",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report


utils.run(run) if (__name__ == "__main__") else None
