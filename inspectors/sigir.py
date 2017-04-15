#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin
from bs4 import Tag

from utils import utils, inspector

# http://www.sigir.mil/
archive = 2004

# options:
#   standard since/year options for a year range to fetch from.

QUARTERLY_REPORTS_URL = "http://cybercemetery.unt.edu/archive/sigir/20130930185834/http://www.sigir.mil/publications/quarterlyreports/index.html"
AUDIT_REPORTS_URL = "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/directorates/audits/auditReports.html"
ASSESSMENTS_URL = "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/directorates/inspections/paReports.html"
TESTIMONY_URL = "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/publications/testimony/index.html"

BASE_REPORT = {
  "inspector": "sigir",
  "inspector_url": "http://www.sigir.mil/",
  "agency": "sigir",
  "agency_name": "Special Inspector General for Iraq Reconstruction"
}

LESSONS_LEARNED_DATA = [
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/learningfromiraq/index.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/files/learningfromiraq/Report_-_March_2013.pdf",
    "Learning From Iraq A Final Report From the Special Inspector General for Iraq Reconstruction",
    datetime.datetime(2013, 3, 6)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/publications/hardLessons.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/files/HardLessons/Hard_Lessons_Report.pdf",
    "Hard Lessons: The Iraq Reconstruction Experience",
    datetime.datetime(2009, 1, 22)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/applyinghardlessons/index.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/files/USOCO/ApplyingHardLessons.pdf",
    "Applying Iraq’s Hard Lessons to the Reform of Stabilization and Reconstruction Operations",
    datetime.datetime(2010, 2, 24)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/publications/lessonsLearnedInIraqReconstruction.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/files/lessonslearned/Lessons_Learned_Dec21.pdf",
    "Lessons in Inspections of U.S.-funded Stabilization and Reconstruction Projects",
    datetime.datetime(2011, 12, 21)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/publications/lessonsLearnedInIraqReconstruction.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/files/lessonslearned/Lessons_Learned_March21.pdf",
    "Lessons Learned in Program and Project Management",
    datetime.datetime(2007, 3, 21)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/publications/lessonsLearnedInIraqReconstruction.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/files/lessonslearned/Lessons_Learned_July21.pdf",
    "Lessons Learned in Contracting and Procurement",
    datetime.datetime(2006, 7, 21)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/publications/lessonsLearnedInIraqReconstruction.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001113104/http://www.sigir.mil/files/lessonslearned/Lessons_Learned_Feb16.pdf",
    "Lessons Learned in Human Capital Management",
    datetime.datetime(2006, 2, 16)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/publications/lessonsLearnedInInvestigations.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/files/lessonslearned/InvestigationsLessonsLearned.pdf",
    "Lessons Learned: from Investigations, 2004−2012",
    datetime.datetime(2012, 4, 30)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/publications/lessonsLearnedInAuditing.html",
    "http://cybercemetery.unt.edu/archive/sigir/20131001084013/http://www.sigir.mil/files/lessonslearned/AuditingLessonsLearned.pdf",
    "Lessons from Auditing U.S.-funded Stabilization and Reconstruction Activities",
    datetime.datetime(2012, 10, 30)
  ),
]

SPECIAL_REPORTS_DATA = [
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001083727/http://www.sigir.mil/files/lessonslearned/SpecialReportLeadersPerceptions.pdf",
    "Leaders' Perceptions of the Commander's Emergency Response Program in Iraq",
    datetime.datetime(2012, 4, 30)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001083727/http://www.sigir.mil/files/lessonslearned/SpecialReport2.pdf",
    "The Human Toll of Reconstruction or Stabilization during Operation Iraqi Freedom",
    datetime.datetime(2012, 7, 27)
  ),
  (
    "http://cybercemetery.unt.edu/archive/sigir/20131001083727/http://www.sigir.mil/files/lessonslearned/SpecialReport3.pdf",
    "Interagency Rebuilding Efforts in Iraq: A Case Study of the Rusafa Political District",
    datetime.datetime(2013, 2, 26)
  ),
]

HEADER_RE = re.compile("Title: +(.*)[ \n]+\((.*)\)")
DATE_RE = re.compile("Date: +(.* +[0-9]+, +[0-9]{4})")
DESCRIPTION_RE = re.compile("Description: +(.*)")


def run(options):
  year_range = inspector.year_range(options, archive)

  # The last SIGIR report was issued in 2013
  if min(year_range) > 2013:
    return

  doc = utils.beautifulsoup_from_url(QUARTERLY_REPORTS_URL)
  results = doc.select("#reportsTbl tr")
  for result in results:
    report = quarterly_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  for result in LESSONS_LEARNED_DATA:
    report = lessons_learned_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  for url, report_type in [(AUDIT_REPORTS_URL, "audit"),
                           (ASSESSMENTS_URL, "assessment")]:
    doc = utils.beautifulsoup_from_url(url)
    results = doc.find("table").find_all("tr")
    for result in results:
      report = report_from(result, year_range, url, report_type)
      if report:
        inspector.save_report(report)

  for result in SPECIAL_REPORTS_DATA:
    report = special_report_from(result, year_range)
    if report:
      inspector.save_report(report)

  doc = utils.beautifulsoup_from_url(TESTIMONY_URL)
  url = None
  published_on_text = None
  title = None
  report_id = None
  summary = None
  for child in doc.find("div", id="subContent").children:
    if isinstance(child, Tag):
      if child.name == "h3":
        if "tableStyle1" in child["class"]:
          header_match = HEADER_RE.match(child.text.strip())
          if title:
            raise Exception("Error: found a new title without a preceding "
                            "statement URL to close out the previous testimony "
                            "(%s)" % title)
          title = header_match.group(1)
          report_id = header_match.group(2)
      elif child.name == "p":
        date_match = DATE_RE.match(child.text.strip())
        description_match = DESCRIPTION_RE.match(child.text.strip())
        if date_match:
          published_on_text = date_match.group(1)
        elif description_match:
          summary = description_match.group(1)
        elif child.text.strip().startswith("Full Statement"):
          url = child.a["href"]
          report = testimony_from(url, published_on_text, title, report_id,
                                  summary, year_range)
          if report:
            inspector.save_report(report)

          # Reset collected information for next cycle and next testimony
          url = None
          published_on_text = None
          title = None
          report_id = None
          summary = None


def quarterly_report_from(result, year_range):
  tds = result.find_all("td")
  if len(tds) == 0:
    # Header row
    return None
  if tds[0].get("colspan") and tds[0]["colspan"] == "7":
    # Footer rows
    return None

  title = tds[0].text
  landing_url = urljoin(QUARTERLY_REPORTS_URL, tds[0].a["href"])
  report_url = urljoin(QUARTERLY_REPORTS_URL, tds[6].a["href"])
  report_id = os.path.splitext(os.path.basename(report_url))[0]

  published_on_text = tds[5].text
  published_on = datetime.datetime.strptime(published_on_text, "%m/%d/%Y")

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = BASE_REPORT.copy()
  report.update({
    "report_id": report_id,
    "url": report_url,
    "landing_url": landing_url,
    "title": title,
    "type": "other",
    "published_on": datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  })
  return report


def lessons_learned_report_from(result, year_range):
  if result[3].year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % result[1])
    return

  report = BASE_REPORT.copy()
  report.update({
    "landing_url": result[0],
    "url": result[1],
    "report_id": os.path.splitext(os.path.basename(result[1]))[0],
    "title": result[2],
    "type": "other",
    "published_on": datetime.datetime.strftime(result[3], "%Y-%m-%d"),
  })
  return report


def special_report_from(result, year_range):
  if result[2].year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % result[0])
    return

  report = BASE_REPORT.copy()
  report.update({
    "url": result[0],
    "report_id": os.path.splitext(os.path.basename(result[0]))[0],
    "title": result[1],
    "type": "other",
    "published_on": datetime.datetime.strftime(result[2], "%Y-%m-%d"),
  })
  return report


def report_from(result, year_range, base_url, report_type):
  tds = result.find_all("td")
  if len(tds) == 0:
    # Header row
    return None
  if tds[0].text == "Report #":
    # Other header row
    return None
  if tds[0].get("colspan") and tds[0]["colspan"] == "4":
    # Footer rows
    return None

  title = tds[1].text
  report_url = urljoin(base_url, tds[1].a["href"])
  report_id = tds[0].text

  published_on_text = tds[3].text
  if published_on_text == "6/2009":
    published_on_text = "6/1/2009"
  elif published_on_text == "7/2006":
    published_on_text = "7/1/2006"
  published_on = datetime.datetime.strptime(published_on_text, "%m/%d/%Y")

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = BASE_REPORT.copy()
  report.update({
    "report_id": report_id,
    "url": report_url,
    "title": title,
    "type": report_type,
    "published_on": datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  })
  return report


def testimony_from(url, published_on_text, title, report_id, summary,
                   year_range):
  published_on = datetime.datetime.strptime(published_on_text, "%B %d, %Y")
  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % url)
    return

  report = BASE_REPORT.copy()
  report.update({
    "report_id": report_id,
    "url": url,
    "title": title,
    "type": "testimony",
    "published_on": datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    "summary": summary
  })
  return report

utils.run(run) if (__name__ == "__main__") else None
