#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.sigar.mil/
# Oldest report: 2008

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

SPOTLIGHT_REPORTS_URL = "http://www.sigar.mil/Newsroom/spotlight/spotlight.xml"
SPEECHES_REPORTS_URL = "http://www.sigar.mil/Newsroom/speeches/speeches.xml"
TESTIMONY_REPORTS_URL = "http://www.sigar.mil/Newsroom/testimony/testimony.xml"

REPORT_URLS = {
  "other": SPOTLIGHT_REPORTS_URL,
  "press": SPEECHES_REPORTS_URL,
  "testimony": TESTIMONY_REPORTS_URL,
  "audit": "http://www.sigar.mil/audits/auditreports/reports.xml",
  "inspection": "http://www.sigar.mil/audits/inspectionreports/inspection-reports.xml",
  "audit": "http://www.sigar.mil/audits/financialreports/Financial-Audits.xml",
  "other": "http://www.sigar.mil/SpecialProjects/projectreports/reports.xml",
  "other": "http://www.sigar.mil/Audits/alertandspecialreports/alert-special-reports.xml",
  "semiannual_report": "http://www.sigar.mil/quarterlyreports/index.xml",
}

BASE_REPORT_URL = "http://www.sigar.mil/allreports/index.aspx"

def run(options):
  year_range = inspector.year_range(options)

  # Pull the reports
  for report_type, report_url in REPORT_URLS.items():
    doc = BeautifulSoup(utils.download(report_url))
    results = doc.select("item")
    for result in results:
      report = report_from(result, report_url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  title = result.find("title").text.strip()

  report_url = report_url_for_landing_page(result.find("link").next.strip(), landing_url)
  report_filename = report_url.split("/")[-1]
  report_id, extension = os.path.splitext(report_filename)

  published_on_text = result.find("pubdate").text.strip()
  published_on = datetime.datetime.strptime(published_on_text, '%A, %B %d, %Y')

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'sigar',
    'inspector_url': "http://www.sigar.mil",
    'agency': 'sigar',
    'agency_name': "Special Inspector General for Afghanistan Reconstruction",
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

def report_url_for_landing_page(relative_url, landing_url):
  """
  We need to mimic the logic used in http://www.sigar.mil/js/AllReports.js

  case SPOTLIGHT:
      Title = "Spotlight";
      Link = Link.replace("../../", "../");
      break;
  case SPEECHES:
      Title = "Speeches";
      Link = Link.replace("../", "../newsroom/");
      break;
  case TESTIMONY:
      Title = "Testimony";
      Link = Link.replace("../../", "../");
      break;
  """

  relative_url = relative_url.replace("â\x80\x93", "–")

  if landing_url == SPOTLIGHT_REPORTS_URL:
    relative_url = relative_url.replace("../../", "../")
  elif landing_url == SPEECHES_REPORTS_URL:
    relative_url = relative_url.replace("../", "../newsroom/")
  elif landing_url == TESTIMONY_REPORTS_URL:
    relative_url = relative_url.replace("../../", "../")

  return urljoin(BASE_REPORT_URL, relative_url)

utils.run(run) if (__name__ == "__main__") else None
