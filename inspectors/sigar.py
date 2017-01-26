#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# https://www.sigar.mil/
archive = 2008

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

SPOTLIGHT_REPORTS_URL = "https://www.sigar.mil/Newsroom/spotlight/spotlight.xml"
SPEECHES_REPORTS_URL = "https://www.sigar.mil/Newsroom/speeches/speeches.xml"
TESTIMONY_REPORTS_URL = "https://www.sigar.mil/Newsroom/testimony/testimony.xml"
PRESS_RELEASES_URL = "https://www.sigar.mil/Newsroom/pressreleases/press-releases.xml"

REPORT_URLS = [
  ("other", SPOTLIGHT_REPORTS_URL),
  ("press", SPEECHES_REPORTS_URL),
  ("testimony", TESTIMONY_REPORTS_URL),
  ("press", PRESS_RELEASES_URL),
  ("audit", "https://www.sigar.mil/audits/auditreports/reports.xml"),
  ("inspection", "https://www.sigar.mil/audits/inspectionreports/inspection-reports.xml"),
  ("audit", "https://www.sigar.mil/audits/financialreports/Financial-Audits.xml"),
  ("other", "https://www.sigar.mil/SpecialProjects/projectreports/reports.xml"),
  ("other", "https://www.sigar.mil/Audits/alertandspecialreports/alert-special-reports.xml"),
  ("semiannual_report", "https://www.sigar.mil/quarterlyreports/index.xml"),
]

BASE_REPORT_URL = "https://www.sigar.mil/allreports/index.aspx"

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, report_url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(report_url)
    results = doc.select("item")
    if not results:
      raise inspector.NoReportsFoundError("SIGAR (%s)" % report_type)
    for result in results:
      report = report_from(result, report_url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  report_url = report_url_for_landing_page(result.find("link").next.strip(), landing_url)

  if report_url in (
      "https://www.sigar.mil/pdf/audits/Financial_Audits/SIGAR _14-15\u2013FA.pdf",
      "https://www.sigar.mil/pdf/audits/Financial_Audits/SIGAR_14-14\u2013FA.pdf",
      ):
    report_url = report_url.replace("\u2013", "-")

  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  if result.title:
    title = result.title.text.strip()
  else:
    title = report_id

  published_on_text = result.find("pubdate").text.strip()
  published_on = parse_date(published_on_text)

  if report_id == "SIGAR-14-42-AL" and title == "SIGAR 14-42-AL":
    # this report is posted in both "spotlight" and "special reports"
    return

  if report_id == "SIGAR_CSIS_Speech" and published_on.year == 2017:
    # There are two speeches with the same file name
    report_id += "_2017"

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'sigar',
    'inspector_url': "https://www.sigar.mil",
    'agency': 'sigar',
    'agency_name': "Special Inspector General for Afghanistan Reconstruction",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  if (report_url.startswith("https://www.justice.gov/") or
      report_url.startswith("http://www.justice.gov/") or
      report_url.startswith("https://www.fbi.gov/") or
      report_url.startswith("http://www.fbi.gov/") or
      report_url.startswith("https://www.usaid.gov/") or
      report_url.startswith("http://www.usaid.gov/")):
    if not os.path.splitext(report_url)[1]:
      report['file_type'] = "html"

  return report

def report_url_for_landing_page(relative_url, landing_url):
  """
  We need to mimic the logic used in https://www.sigar.mil/js/AllReports.js

  case SPOTLIGHT:
      Title = "Spotlight";
      Link = Link.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx");
      Link = Link.replace("../../", "../");
      break;
  case SPEECHES:
      Title = "Speeches";
      Link = Link.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx");
      Link = Link.replace("../../", "../");
      break;
  case TESTIMONY:
      Title = "Testimony";
      Link = Link.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx");
      Link = Link.replace("../../", "../");
      break;
  case PRESSRELEASES:
      Link = Link.replace("../", "../newsroom/");
      Link = Link.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx");
      break;
  """

  relative_url = relative_url.replace("â\x80\x93", "–")

  if landing_url == SPOTLIGHT_REPORTS_URL:
    relative_url = relative_url.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx")
    relative_url = relative_url.replace("../../", "../")
  elif landing_url == SPEECHES_REPORTS_URL:
    relative_url = relative_url.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx")
    relative_url = relative_url.replace("../../", "../")
  elif landing_url == TESTIMONY_REPORTS_URL:
    relative_url = relative_url.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx")
    relative_url = relative_url.replace("../../", "../")
  elif landing_url == PRESS_RELEASES_URL:
    relative_url = relative_url.replace("../", "../newsroom/")
    relative_url = relative_url.replace("../ReadFile.aspx", "../newsroom/ReadFile.aspx")

  return urljoin(BASE_REPORT_URL, relative_url)

def parse_date(text):
  for format in [
      '%A, %B %d, %Y',
      '%A, %B %dst, %Y',
      '%A, %B %dnd, %Y',
      '%A, %B %drd, %Y',
      '%A, %B %dth, %Y'
  ]:
    try:
      return datetime.datetime.strptime(text, format)
    except ValueError:
      pass
  raise Exception("Couldn't parse date from {}".format(text))

utils.run(run) if (__name__ == "__main__") else None
