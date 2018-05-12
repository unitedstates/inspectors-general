#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin, urlparse, urlunparse

from utils import utils, inspector, admin

# https://www.cpsc.gov/About-CPSC/Inspector-General/
archive = 2003

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - Fix the links for BLACKLIST_REPORT_URLS

REPORTS_URL = "https://www.cpsc.gov/About-CPSC/Inspector-General/"

BLACKLIST_REPORT_URLS = [
]

REPORT_PUBLISHED_MAP = {
    "SemiAnnualReporttoCongress10-1-15to3-31-16": datetime.datetime(2016, 4, 29),
    "SARtoCongressAPR1SEP302015withForwardingMemo1": datetime.datetime(2015, 10, 30),
    "SemiAnnualReport04242015_0": datetime.datetime(2015, 4, 30),
    "SemiAnnualReport09302014": datetime.datetime(2014, 10, 30),
    "SemiAnnualReport03312014": datetime.datetime(2014, 4, 30),
    "SARFY13APR_SEPTRPRT": datetime.datetime(2013, 10, 30),
    "OIGSemiReport2013a": datetime.datetime(2013, 4, 30),
    "sar2012b": datetime.datetime(2012, 10, 30),
    "SemiAnnualReport03312012": datetime.datetime(2012, 4, 30),
    "sar2011a": datetime.datetime(2011, 4, 30),
    "sar2010a": datetime.datetime(2010, 4, 30),
    "sar2011b": datetime.datetime(2011, 10, 30),
    "sar2010b": datetime.datetime(2010, 10, 30),
    "sar2009b_0": datetime.datetime(2009, 10, 30),
}


def run(options):
  year_range = inspector.year_range(options, archive)

  doc = utils.beautifulsoup_from_url(REPORTS_URL)
  results = doc.select(".table-responsive tbody tr")
  if not results:
    raise inspector.NoReportsFoundError("CPSC")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)


def report_type_from_title(title):
  if 'Audit' in title or 'Follow-Up Review' in title:
    return 'audit'
  elif 'Inspection' in title:
    return 'inspection'
  elif 'Semiannual Report' in title:
    return 'semiannual_report'
  elif 'Peer Review' in title:
    return 'peer_review'
  elif 'Federal Information Security Management' in title:
    return 'fisma'
  else:
    return 'other'


def report_from(result, year_range):
  link = result.find("a")
  report_url = urljoin(REPORTS_URL, link.get('href'))
  report_url = urlunparse(list(urlparse(report_url)[:4]) + ["", ""])
  if report_url in BLACKLIST_REPORT_URLS:
    return

  # Follow redirects to get real file names
  if report_url.startswith("https://www.cpsc.gov/Media/"):
    report_url = utils.resolve_redirect(report_url)

  # URLs with /PageFiles in them need to use the filename and its
  # directory to be unique. Other URLs can just use the filename.
  if "PageFiles" in report_url:
    # e.g. /../132643/fy11fisma.pdf -> 132643-fy11fisma.pdf
    report_filename = str.join("-", report_url.split("/")[-2:])
  else:
    report_filename = report_url.split("/")[-1]

  report_id, _ = os.path.splitext(report_filename)

  title = link.text
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    date_spans = result.select(".date-display-single")
    if date_spans:
      published_on_text = date_spans[0].text
      published_on = datetime.datetime.strptime(published_on_text, '%A, %B %d, %Y')
    else:
      admin.log_no_date("cpsc", report_id, title, report_url)
      return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report_type = report_type_from_title(title)

  report = {
    'inspector': 'cpsc',
    'inspector_url': 'https://www.cpsc.gov/About-CPSC/Inspector-General/',
    'agency': 'cpsc',
    'agency_name': 'Consumer Product Safety Commission',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
