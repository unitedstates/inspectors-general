#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector

# https://www.si.edu/OIG
archive = 2003

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

# The general strategy for this report is a bit complicated. First we go through
# the RSS feed and add reports. This gives us a bunch of reports with definitive
# published dates. Unfortunately, this feed is only updated sporadically.
# Next, we use the main audits page since this also gives us accurate published
# dates for the newer reports that are listed. Lastly, we fall back to the
# archives page, which unfortunately only lists the year the report was
# published.
#
# Since a report can be listed on multiple pages, it is important to use
# consistent report ids across pages. We only grab reports the first time a
# a given report id is seen.

RSS_URL = "https://www.si.edu/Content/OIG/Misc/OIG-RSS.xml"
RECENT_AUDITS_URL = "https://www.si.edu/OIG/Audits"
AUDIT_ARCHIVE_URL = "https://www.si.edu/oig/Archive"
OTHER_REPORTS_URL = "https://www.si.edu/OIG/ReportsToCongress"

RSS_BROKEN_LINKS = {
  "http://www.si.edu/Content/OIG/Misc/Peer_Review_09-21-2011.pdf":
    "https://www.si.edu/Content/OIG/Misc/Peer_Review_09-21-11.pdf",
  "http://www.si.edu/oig/RecoveryAct.htm":
    "https://www.si.edu/OIG/Recovery",
  "http://www.si.edu/oig/AuditReports/UnderstandingAudits.pdf":
    "https://www.si.edu/Content/OIG/Misc/UnderstandingAudits.pdf",
  "http://www.si.edu/oig/AuditReports/A-0907-FSA-Oversight.pdf":
    "https://www.si.edu/Content/OIG/Audits/2010/A-09-07.pdf",
  "http://www.si.edu/oig/ARRA_Reports/M-10--04-1.pdf":
    "https://www.si.edu/Content/OIG/Audits/M-10-04-1.pdf",
  "http://www.si.edu/oig/AuditReports/SIIG_Testimony_121009.pdf":
    "https://www.si.edu/Content/OIG/Testimony/SIIG_Testimony_121009.pdf",
  "http://www.si.edu/oig/AuditReports/IBA-0902.pdf":
    "https://www.si.edu/Content/OIG/Audits/2009/IBA-09-02.pdf",
  "http://www.si.edu/oig/AuditReports/IBA-0808.pdf":
    "https://www.si.edu/Content/OIG/Audits/2009/IBA-08-08.pdf",
  "http://www.si.edu/oig/AuditReports/A-08-05-FSA-Oversight-Letter.pdf":
    "https://www.si.edu/Content/OIG/Audits/2009/A-08-05.pdf",
}

REPORT_PUBLISHED_MAP = {
  "A-15-06": datetime.datetime(2015, 12, 10),
  "A-13-07": datetime.datetime(2013, 7, 26),
  "A-13-03": datetime.datetime(2013, 2, 27),
  "A-13-01": datetime.datetime(2013, 10, 29),
  "A-12-08": datetime.datetime(2013, 6, 3),
  "A-11-05": datetime.datetime(2012, 5, 15),
  "A-11-07": datetime.datetime(2013, 3, 30),
  "M-11-03": datetime.datetime(2011, 7, 1),
  "A-09-03-02": datetime.datetime(2009, 9, 14),
  "A-09-03-01": datetime.datetime(2009, 9, 3),
  "WRW_TravelReview": datetime.datetime(2008, 10, 28),
  "A-07-09-1": datetime.datetime(2008, 7, 18),
  "SBVCEOAUPFY06-7": datetime.datetime(2008, 7, 7),
  "SecretaryAUPFY06-7": datetime.datetime(2008, 7, 3),
  "IBA-07-08": datetime.datetime(2008, 3, 31),
  "A-07-01": datetime.datetime(2008, 3, 31),
  "A-07-05": datetime.datetime(2008, 2, 25),
  "A-06-04": datetime.datetime(2007, 1, 16),
  "A-06-06R": datetime.datetime(2007, 1, 19),
  "A-06-02R": datetime.datetime(2007, 1, 19),
  "A-06-08": datetime.datetime(2007, 5, 16),
  "SBVCEOAUP": datetime.datetime(2007, 7, 19),
  "A-06-07": datetime.datetime(2007, 8, 10),
  "A-06-01": datetime.datetime(2007, 8, 28),
  "A-06-05": datetime.datetime(2007, 4, 20),
  "A-07-06": datetime.datetime(2007, 9, 19),
  "A-07-04": datetime.datetime(2007, 9, 28),
  "A-05-03": datetime.datetime(2006, 2, 16),
  "M-06-01": datetime.datetime(2006, 2, 14),
  "IBA-05-05": datetime.datetime(2006, 7, 25),
  "A-05-07": datetime.datetime(2006, 8, 21),
  "A-05-06R": datetime.datetime(2006, 9, 29),
  "A-04-05": datetime.datetime(2005, 1, 6),
  "A-04-10": datetime.datetime(2005, 2, 25),
  "A-04-11": datetime.datetime(2005, 3, 3),
  "A-05-01": datetime.datetime(2005, 9, 29),
  "A-05-04": datetime.datetime(2005, 9, 28),
  "M-05-01": datetime.datetime(2006, 6, 8),
  "M-05-02": datetime.datetime(2005, 9, 15),
  "M-05-03": datetime.datetime(2005, 12, 5),
  "A-03-07": datetime.datetime(2004, 3, 31),
  "A-04-02": datetime.datetime(2004, 6, 16),
  "A-04-03": datetime.datetime(2004, 9, 9),
  "A-04-06": datetime.datetime(2004, 8, 25),
  "A-04-07": datetime.datetime(2004, 7, 22),
  "A-02-04": datetime.datetime(2003, 7, 31),
  "A-02-06": datetime.datetime(2003, 1, 17),
  "A-02-10": datetime.datetime(2003, 4, 16),
  "A-03-02": datetime.datetime(2003, 3, 31),
  "A-03-04": datetime.datetime(2003, 3, 27),
  "A-03-05": datetime.datetime(2003, 12, 18),
  "A-03-06": datetime.datetime(2003, 12, 3),
  "A-03-08": datetime.datetime(2003, 9, 3),
}

URL_BLACKLIST = [
  RECENT_AUDITS_URL,
  OTHER_REPORTS_URL,
  AUDIT_ARCHIVE_URL,
  "https://get.adobe.com/reader/"
]

report_ids_seen = set()

def run(options):
  year_range = inspector.year_range(options, archive)

  # # Pull the RSS feed
  doc = utils.beautifulsoup_from_url(RSS_URL)
  results = doc.select("item")
  if not results:
    raise inspector.NoReportsFoundError("Smithsonian (RSS)")
  for result in results:
    report = rss_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # # Pull the recent audit reports.
  doc = utils.beautifulsoup_from_url(RECENT_AUDITS_URL)
  results = doc.select("div.block > a")
  if not results:
    raise inspector.NoReportsFoundError("Smithsonian (recent audit reports)")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the archive audit reports
  doc = utils.beautifulsoup_from_url(AUDIT_ARCHIVE_URL)
  results = doc.select("div.block a")
  if not results:
    raise inspector.NoReportsFoundError("Smithsonian (audit archive)")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

  # Pull the other reports
  doc = utils.beautifulsoup_from_url(OTHER_REPORTS_URL)
  results = doc.select("div.block > a")
  if not results:
    raise inspector.NoReportsFoundError("Smithsonian (other)")
  for result in results:
    report = report_from(result, year_range)
    if report:
      inspector.save_report(report)

def report_type_from_url(report_url):
  if 'Audit' in report_url or 'Announcements' in report_url:
    return 'audit'
  elif 'Semiannual' in report_url:
    return 'semiannual_report'
  elif 'Testimony' in report_url:
    return 'testimony'
  elif 'Peer_Review' in report_url:
    return 'peer_review'
  elif 'PressRelease' in report_url:
    return 'press'
  else:
    return 'other'

def rss_report_from(result, year_range):
  report_url = result.find("link").next_sibling.strip()
  if report_url.rstrip("/") == 'http://www.si.edu/oig':
    # This is the default url the IG uses for announcements of things like
    # a website redesign or changes to the RSS feed.
    return

  if report_url == "http://www.si.edu/oig/OIGStratPlan.pdf":
    # This strategic plan is no longer on the website, but it is reproduced in
    # multiple semiannual reports, so we skip it here.
    return

  if report_url in RSS_BROKEN_LINKS:
    report_url = RSS_BROKEN_LINKS[report_url]
  else:
    report_url = report_url.replace("/OIG/SAR/Semiannual_Reports/", "/OIG/SAR/")
    report_url = report_url.replace("/oig/Semiannual_Reports/", "/Content/OIG/SAR/")
    report_url = report_url.replace("/oig/AuditReports/", "/Content/OIG/Audits/")
    report_url = report_url.replace("/oig/ARRA_Reports/", "/Content/OIG/Audits/")

  file_type = None
  if not report_url.endswith(".pdf"):
    file_type = "html"

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  if report_id in report_ids_seen:
    return
  report_ids_seen.add(report_id)

  title = result.find("title").text
  report_type = report_type_from_url(report_url)

  published_on = None
  published_on_text = result.find("pubdate").text
  try:
    published_on = datetime.datetime.strptime(published_on_text, '%a, %d %b %Y %H:%M:%S %z').date()
  except ValueError:
    pass

  if not published_on:
    try:
      published_on = datetime.datetime.strptime(published_on_text, '%a, %d %B %Y %H:%M:%S %z').date()
    except ValueError:
      pass

  if not published_on:
    inspector.log_no_date(report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'smithsonian',
    'inspector_url': 'https://www.si.edu/OIG',
    'agency': 'smithsonian',
    'agency_name': 'Smithsonian Institution',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if file_type:
    report['file_type'] = file_type
  return report

def report_from(result, year_range):
  report_url = urljoin(RECENT_AUDITS_URL, result.get('href'))
  if report_url in URL_BLACKLIST:
    return None
  # Strip extra path adjustments
  report_url = report_url.replace("../", "")

  summary = None
  if not report_url.endswith(".pdf"):
    # Some reports link to other page which link to the full report
    report_page = utils.beautifulsoup_from_url(report_url)
    relative_report_url = report_page.select("div.block a[href]")[0]['href']
    report_url = urljoin(report_url, relative_report_url)
    # Strip extra path adjustments
    report_url = report_url.replace("../", "")

    summary = "\n".join(paragraph.text for paragraph in report_page.select("div.grid_12 p"))

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  if report_id in report_ids_seen:
    return
  report_ids_seen.add(report_id)

  title = result.text.strip()
  report_type = report_type_from_url(report_url)

  if not title:
    return None

  estimated_date = False
  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    try:
      published_on_text = "/".join(re.search('(\w+) (\d+), (\d+)', title).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%B/%d/%Y')
    except AttributeError:
      pass

  if not published_on:
    month_year_match = MONTH_YEAR_RE.search(result.text)
    if month_year_match:
      date_text = ' '.join(month_year_match.group(0).split())
      published_on = datetime.datetime.strptime(date_text, '%B %Y')
      estimated_date = True

  if not published_on:
    inspector.log_no_date(report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'smithsonian',
    'inspector_url': 'https://www.si.edu/OIG',
    'agency': 'smithsonian',
    'agency_name': 'Smithsonian Institution',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if summary:
    report['summary'] = summary
  if estimated_date:
    report['estimated_date'] = estimated_date
  return report

MONTH_YEAR_RE = re.compile('(?:January|February|March|April|May|June|July|' \
                           'August|September|October|November|December)\s+' \
                           '[0-9]{4}')

utils.run(run) if (__name__ == "__main__") else None
