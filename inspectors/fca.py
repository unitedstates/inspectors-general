#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://www.fca.gov/home/inspector.html
archive = 1989

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "https://www.fca.gov/home/inspector/ig_reports.html"
REPORT_ARCHIVE_URL = "https://www.fca.gov/home/inspector/oigarchive.html"
SEMIANNUAL_REPORTS_URL = "https://www.fca.gov/home/inspector/semiannual.html"

REPORT_PUBLISHED_MAPPING = {
  "ControlseOPF": datetime.datetime(2016, 4, 21),
  "RegulatoryDevelopmentSurvey2002": datetime.datetime(2002, 10, 22),
  "FinancialAuditReport15": datetime.datetime(2015, 11, 9),
  "FinancialAuditReport14": datetime.datetime(2014, 11, 13),
  "FinancialAuditReport13": datetime.datetime(2013, 11, 20),
  "FinancialAuditReport12": datetime.datetime(2012, 11, 5),
  "FinancialAuditReport11": datetime.datetime(2011, 11, 8),
  "FinancialAuditReport10": datetime.datetime(2010, 11, 8),
  "S&OPP16-17": datetime.datetime(2015, 9, 16),
  "S&OPP15-16": datetime.datetime(2014, 9, 30),
  "S&OPP14-15": datetime.datetime(2013, 9, 11),
  "S&OPP13-14": datetime.datetime(2012, 8, 21),
  "S&OPP12-13": datetime.datetime(2011, 8, 22),
  "PerformanceReport14&15": datetime.datetime(2016, 1, 20),
  "PerformanceReport12&13": datetime.datetime(2014, 1, 15),
  "PerformanceReport10&11": datetime.datetime(2012, 1, 9),
  "PerformanceReport08-09": datetime.datetime(2010, 1, 20),
  "PerformanceReport06-07": datetime.datetime(2008, 2, 11),
  "FirstQtrFY2016FCSSurvey": datetime.datetime(2016, 3, 24),
  "FourthQtrFY2015FCSSurvey": datetime.datetime(2016, 1, 4),
  "ThirdQtrFY2015FCSSurvey": datetime.datetime(2015, 9, 15),
  "SecondQtrFY2015FCSSurvey": datetime.datetime(2015, 6, 5),
  "FirstQtrFY2015FCSSurvey": datetime.datetime(2015, 3, 26),
  "FourthQtrFY2014FCSSurvey": datetime.datetime(2015, 1, 20),
  "ThirdQtrFY2014FCSSurvey": datetime.datetime(2014, 10, 22),
  "SecondQtrFY2014FCSSurvey": datetime.datetime(2014, 6, 18),
  "FirstQtrFY2014FCSSurvey": datetime.datetime(2014, 3, 26),
  "FourthQtrFY2013FCSSurvey": datetime.datetime(2013, 12, 19),
  "ThirdQtrFY2013FCSSurvey": datetime.datetime(2013, 9, 23),
  "SecondQtrFY2013FCSSurvey": datetime.datetime(2013, 6, 11),
  "FirstQtrFY2013FCSSurvey": datetime.datetime(2013, 3, 19),
  "FourthQtrFY2012FCSSurvey": datetime.datetime(2012, 12, 20),
  "ThirdQtrFY2012FCSSurvey": datetime.datetime(2012, 9, 11),
  "SecondQtrFY2012FCSSurvey": datetime.datetime(2012, 6, 13),
  "FirstQtrFY2012FCSSurvey": datetime.datetime(2012, 3, 27),
  "FourthQtrFY2011FCSSurvey": datetime.datetime(2011, 12, 1),
  "ThirdQtrFY2011FCSSurvey": datetime.datetime(2011, 9, 1),
  "SecondQtrFY2011FCSSurvey": datetime.datetime(2011, 6, 16),
  "FirstQtrFY2011FCSSurvey": datetime.datetime(2011, 3, 28),
  "2013PeerReviewOIGAuditFunction": datetime.datetime(2013, 6, 26),
  "2010PeerReviewOIGAuditFunction": datetime.datetime(2011, 2, 4),
  "2007PeerReviewOIGInvestigativeFunction": datetime.datetime(2007, 12, 26),
  "2006PeerReviewOIGAuditFunction": datetime.datetime(2007, 4, 30),
  "S&OPP11-12": datetime.datetime(2010, 8, 23),
  "S&OPP10-11": datetime.datetime(2009, 8, 19),
  "S&OPP09-10": datetime.datetime(2008, 8, 11),
  "S&OPP08-09": datetime.datetime(2007, 8, 15),
  "O&PP07-08": datetime.datetime(2006, 8, 16),
  "O&PP06-07": datetime.datetime(2005, 8, 22),
  "O&PP05-06": datetime.datetime(2004, 6, 30),
  "O&PP04-05": datetime.datetime(2003, 7, 7),
  "O&PP03-04": datetime.datetime(2002, 8, 13),
  "O&PP02-03": datetime.datetime(2001, 1, 1),
  "O&PP01": datetime.datetime(2000, 1, 1),
  "PerformanceMeasures05": datetime.datetime(2006, 1, 10),
  "PerformanceMeasures04": datetime.datetime(2005, 1, 4),
  "PerformanceMeasures03": datetime.datetime(2004, 7, 1),
  "PerformanceMeasures02": datetime.datetime(2003, 1, 1),
  "PerformanceMeasures01": datetime.datetime(2002, 1, 1),
  "PerformanceMeasures00": datetime.datetime(2001, 1, 1),
  "PerformanceMeasures99": datetime.datetime(2000, 1, 1),
  "FourthQtrFY2010FCSSurvey": datetime.datetime(2010, 12, 14),
  "ThirdQtrFY2010FCSSurvey.pdf": datetime.datetime(2010, 9, 14),
  "SecondQtrFY2010FCSSurvey": datetime.datetime(2010, 6, 11),
  "FirstQtrFY2010FCSSurvey": datetime.datetime(2010, 3, 29),
  "FourthQtrFY2009FCSSurvey": datetime.datetime(2009, 12, 28),
  "ThirdQtrFY2009FCSSurvey": datetime.datetime(2009, 9, 10),
  "SecondQtrFY2009FCSSurvey": datetime.datetime(2009, 6, 12),
  "FirstQtrFY2009FCSSurvey": datetime.datetime(2009, 3, 25),
  "FourthQtrFY2008FCSSurvey": datetime.datetime(2008, 12, 1),
  "ThirdQtrFY2008FCSurvey": datetime.datetime(2008, 9, 1),
  "SecondQtrFY2008FCSSurvey": datetime.datetime(2008, 6, 1),
  "FirstQtrFY2008FCSSurvey": datetime.datetime(2008, 3, 1),
  "FourthQtrFY2007FCSSurvey": datetime.datetime(2007, 12, 1),
  "ThirdQtrFY2007FCSSurvey": datetime.datetime(2007, 9, 1),
  "SecondQtrFY2007FCSSurvey": datetime.datetime(2007, 6, 1),
  "FirstQtrFY2007FCSSurvey": datetime.datetime(2007, 3, 1),
  "FY2005FCSSurvey": datetime.datetime(2005, 11, 9),
  "FY2004FCSSurvey": datetime.datetime(2004, 11, 15),
  "FY2003FCSSurvey": datetime.datetime(2003, 10, 30),
  "FY2002FCSSurvey": datetime.datetime(2002, 10, 28),
  "FY2001FCSSurvey": datetime.datetime(2001, 9, 1),
  "FinancialAuditReport09": datetime.datetime(2009, 11, 4),
  "FinancialAuditReport08": datetime.datetime(2008, 11, 7),
  "FinancialAuditReport07": datetime.datetime(2007, 11, 7),
  "FinancialAuditReport06": datetime.datetime(2006, 11, 9),
  "FinancialAuditReport05": datetime.datetime(2005, 11, 4),
  "FinancialAuditReport04": datetime.datetime(2004, 11, 3),
  "FinancialAuditReport03": datetime.datetime(2004, 1, 6),
  "FinancialAuditReport02": datetime.datetime(2003, 1, 8),
  "FISMAEvaluation09": datetime.datetime(2009, 11, 18),
  "FISMAEvaluation08": datetime.datetime(2008, 9, 29),
  "FISMAEvaluation07": datetime.datetime(2007, 10, 1),
  "FISMAEvaluation06": datetime.datetime(2006, 9, 29),
  "FISMAEvaluation05": datetime.datetime(2005, 9, 20),
  "FISMAEvaluation04": datetime.datetime(2004, 9, 30),
  "FISMAEvaluation03": datetime.datetime(2003, 9, 10),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the general reports
  doc = utils.beautifulsoup_from_url(REPORTS_URL)
  results = doc.select("div#mainContent li.mainContenttext a")
  if not results:
    raise inspector.NoReportsFoundError("Farm Credit Administration (reports)")
  for result in results:
    report = report_from(result, REPORTS_URL, year_range)
    if report:
      inspector.save_report(report)

  # Pull the archive reports
  doc = utils.beautifulsoup_from_url(REPORT_ARCHIVE_URL)
  results = doc.select("div#mainContent li.mainContenttext a") + doc.select("div#mainContent span.mainContenttext a")
  if not results:
    raise inspector.NoReportsFoundError("Farm Credit Administration (archive)")
  for result in results:
    if not result.text:
      continue
    report = report_from(result, REPORT_ARCHIVE_URL, year_range)
    if report:
      inspector.save_report(report)

  # Pull the semiannual reports
  doc = utils.beautifulsoup_from_url(SEMIANNUAL_REPORTS_URL)
  results = doc.select("div#mainContent li.mainContenttext a")
  if not results:
    raise inspector.NoReportsFoundError("Farm Credit Administration (semiannual reports)")
  for result in results:
    report = semiannual_report_from(result, year_range)
    if report:
      inspector.save_report(report)

def clean_text(text):
  return text.replace("Â\xa0", " ").strip()

def type_for_report(text):
  if "Audit" in text:
    return "audit"
  elif "Semiannual Report" in text:
    return "semiannual_report"
  elif "Inspection" in text:
    return "inspection"
  elif "FISMA" in text:
    return "fisma"
  elif "Peer Review" in text:
    return "peer_review"
  elif "Survey" in text:
    return "research"
  elif "Performance" in text:
    return "performance"
  else:
    return "other"

def report_from(result, landing_url, year_range):
  report_url = urljoin(landing_url, result.get('href'))

  # HTTPS, even if they haven't updated their links yet
  report_url = re.sub("^http://www.fca.gov", "https://www.fca.gov", report_url)

  if landing_url + '#' in report_url:
    # These are just anchor links, skip them.
    return

  if result.find_parent("ul") and result.find_parent("ul").get('type') == 'disc':
    # These are just anchor links, skip them.
    return

  title = clean_text(result.text)

  if title == 'Inspector General Reports':
    # Just a return link to the main IG page
    return

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  published_on = None
  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  if not published_on:
    try:
      li = result.parent
      if li.name == "u":
        li = li.parent
      published_on_text = li.contents[1].lstrip(",").split("(")[0].strip()
    except (IndexError, TypeError):
      published_on_text = result.text.strip()
    published_on_text = clean_text(published_on_text)

    try:
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except ValueError:
      pass

  if not published_on:
    try:
      published_on_text = "/".join(re.search("(\w{3}).* (\d{4})", published_on_text).groups())
      published_on = datetime.datetime.strptime(published_on_text, '%b/%Y')
    except AttributeError:
      pass

  if not published_on:
    admin.log_no_date("fca", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report_type_text = result.find_previous("p", class_="mainContentheader2").text.strip()
  report_type = type_for_report(report_type_text)

  report = {
    'inspector': 'fca',
    'inspector_url': 'https://www.fca.gov/home/inspector.html',
    'agency': 'fca',
    'agency_name': 'Farm Credit Administration',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

def semiannual_report_from(result, year_range):
  report_url = urljoin(SEMIANNUAL_REPORTS_URL, result.get('href'))

  # HTTPS, even if they haven't updated their links yet
  report_url = re.sub("^http://www.fca.gov", "https://www.fca.gov", report_url)

  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  published_on_text = result.text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
  title = "Semiannual Report {}".format(published_on_text)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'fca',
    'inspector_url': 'https://www.fca.gov/home/inspector.html',
    'agency': 'fca',
    'agency_name': 'Farm Credit Administration',
    'type': 'semiannual_report',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
