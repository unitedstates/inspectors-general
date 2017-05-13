#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm
archive = 2000

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Add published dates for all reports in REPORT_PUBLISHED_MAPPING

REPORT_PUBLISHED_MAPPING = {
  "oig_mgmtuseitresources": datetime.datetime(2014, 10, 1),
  "oig_auditreportp05": datetime.datetime(2014, 7, 17),
  "oigocoaudit2014": datetime.datetime(2014, 5, 1),
  "oigcommentletter042214": datetime.datetime(2014, 4, 22),
  "oig_auditruleenforcementreview": datetime.datetime(2015, 8, 5),
  "oig_rrcp2016": datetime.datetime(2016, 10, 11),
  "oig_ipera2015": datetime.datetime(2016, 5, 16),
  "oig_pensionawardsaudit": datetime.datetime(2015, 9, 24),
  "2016finstatementaudit": datetime.datetime(2016, 11, 17),
  "oigfinancialstatementalert": datetime.datetime(2016, 1, 15),
  "2015finstatementaudit": datetime.datetime(2016, 1, 15),
  "2009par": datetime.datetime(2009, 11, 13),
  "2004finstatementaudit": datetime.datetime(2004, 11, 16),
  "oigmgmtchall2016": datetime.datetime(2016, 10, 3),
  "oigmgmtchall2015": datetime.datetime(2015, 10, 26),
  "oigmgmtchall2014": datetime.datetime(2014, 11, 17),
  "oigmgmtchall2013": datetime.datetime(2013, 12, 13),
  "oigmgmtchall2012": datetime.datetime(2012, 11, 14),
  "oigmgmtchall2011": datetime.datetime(2011, 11, 10),
  "oigmgmtchall2010": datetime.datetime(2010, 10, 10),
  "oigmgmtchall2009": datetime.datetime(2009, 11, 16),
  "oigmgmtchall2008": datetime.datetime(2008, 11, 14),
  "oigmgmtchall2007": datetime.datetime(2007, 11, 15),
  "oigmgmtchall2006": datetime.datetime(2006, 10, 31),
  "oigmgmtchall2005": datetime.datetime(2005, 10, 10),
  "oigmgmtchall2004": datetime.datetime(2004, 11, 12),
  "FOIAaudit20122011": datetime.datetime(2013, 1, 28),
  "cpfreport2016": datetime.datetime(2016, 11, 17),
  "cpfreport2015": datetime.datetime(2015, 10, 30),
  "cpfreport2014": datetime.datetime(2014, 10, 30),
  "cpfreport2013": datetime.datetime(2013, 10, 31),
  "cpfreport2012": datetime.datetime(2012, 10, 25),
  "cpfreport2011": datetime.datetime(2011, 10, 25),
  "fisma2014": datetime.datetime(2014, 2, 20),
  "oig_riskassess2015": datetime.datetime(2016, 2, 19),
  "oig_crfrc032416": datetime.datetime(2016, 3, 24),
  "oig_transmittalmemo093016": datetime.datetime(2016, 11, 22),
  "oig_arc030617": datetime.datetime(2017, 3, 6),
  "oig_riskassess2016": datetime.datetime(2017, 4, 14),
}

REPORTS_URL = "http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm"


def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  doc = utils.beautifulsoup_from_url(REPORTS_URL)
  results = doc.select("ul.text > ul > li")
  if not results:
    raise inspector.NoReportsFoundError("CFTC audit reports")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  results = doc.select("ul.text td a")
  if not results:
    raise inspector.NoReportsFoundError("CFTC semiannual reports")
  for result in results:
    report = report_from(result, year_range, report_type="semiannual_report")
    if report:
      inspector.save_report(report)


def extract_report_type(text):
  if 'Peer Review' in text:
    return "peer_review"
  elif 'Audit' in text:
    return "audit"
  elif 'Investigation' in text:
    return 'investigation'
  elif 'Inspection' in text:
    return "inspection"
  elif 'Management Challenges' in text:
    return "management_challenges"


def report_from(result, year_range, report_type=None):
  if result.name == 'a':
    link = result
  else:
    link = result.select("a")[-1]

  href = link['href']
  href = href.replace("file://///cftc.gov/home/dc/MWOODLAND/Desktop/", "")
  report_url = urljoin(REPORTS_URL, href)
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  title = link.text

  published_on = None
  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  if not published_on:
    try:
      published_on_text = "/".join(re.search("(\w+) (\d+), (\d+)", title).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B/%d/%Y')
    except AttributeError:
      pass
  if not published_on:
    try:
      published_on_text = "/".join(re.search("(\w+) (\d+), (\d+)", str(link.next_sibling)).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B/%d/%Y')
    except AttributeError:
      pass
  if not published_on:
    admin.log_no_date("cftc", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  if not report_type:
    report_type = extract_report_type(title)
  if not report_type:
    report_type = extract_report_type(result.find_previous("p").text)
  if not report_type:
    report_type = "other"

  report = {
    'inspector': 'cftc',
    'inspector_url': 'http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm',
    'agency': 'cftc',
    'agency_name': 'Commodity Futures Trading Commission',
    'file_type': 'pdf',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': report_type,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
