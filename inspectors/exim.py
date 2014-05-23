#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime
import re

def run(options):
  year_range = inspector.year_range(options)
  for url in URLS:
    body = utils.download(url)
    doc = BeautifulSoup(body)
    maincontent = doc.select("div#CS_Element_eximpagemaincontent")[0]
    results = maincontent.find_all("p")
    for result in results:
      if len(result.find_all("a")) == 0:
        continue
      if result.a.get('href').startswith('mailto:'):
        continue
      year = DATE_RE.search(result.text).group(3)
      if int(year) not in year_range:
        continue
      report = report_from(result, url)
      inspector.save_report(report)

def report_from(result, page_url):
  report = {
    'inspector': 'exim',
    'inspector_url': 'http://www.exim.gov/oig/index.cfm',
    'agency': 'exim',
    'agency_name': 'Export-Import Bank of the United States'
  }

  a_list = result.find_all("a")
  url = None
  link_text = ""
  for a in a_list:
    if not url:
      url = a.get("href")
    elif url != a.get("href"):
      raise Exception("Found two URLs in one <p> tag, " +
                      "something is wrong\n%s\n%s" % (url, a.get("href")))
    link_text = link_text + a.text
  link_text = link_text.strip()
  if url.startswith('/'):
    url = "http://www.exim.gov" + url

  report_type = type_for(page_url, result)

  date_text = DATE_RE.search(result.text).group(0)
  published_on = datetime.strptime(date_text, '%B %d, %Y')

  report_match = IDENTIFIER_RE.search(result.text)
  if report_match:
    report_id = report_match.group(1)
  else:
    report_id = url[url.rfind('/') + 1 : url.rfind('.')]

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['url'] = url
  report['report_id'] = report_id
  report['title'] = link_text

  return report

def type_for(page_url, p):
  text = p.text.strip()
  if page_url == WHATS_NEW_URL or page_url == WHATS_NEW_ARCHIVE_URL:
    if text.find("Semiannual Report to Congress") != -1:
      return "other"
    header = text[:text.find(' - ')]
    if header == "Testimony":
      return "testimony"
    if header == "Report":
      return "audit"
    if header == "Press Report":
      return "press"
    return "other"
  elif page_url == PRESS_RELEASES_URL or page_url == PRESS_RELEASES_ARCHIVE_URL:
    return "press"
  elif page_url == SEMIANNUAL_REPORTS_AND_TESTIMONIES:
    if text.find("House") != -1 or text.find("Senate") != -1:
      return "testimony"
    return "other"

WHATS_NEW_URL = "http://www.exim.gov/oig/index.cfm"
WHATS_NEW_ARCHIVE_URL = "http://www.exim.gov/oig/whats-new-archive.cfm"
PRESS_RELEASES_URL = "http://www.exim.gov/oig/pressreleases/"
PRESS_RELEASES_ARCHIVE_URL = "http://www.exim.gov/oig/pressreleases/Press-Releases-Archive.cfm"
SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL = "http://www.exim.gov/oig/reports/semiannual-reports-and-testimony.cfm"

URLS = (
  WHATS_NEW_URL,
  WHATS_NEW_ARCHIVE_URL,
  PRESS_RELEASES_URL,
  PRESS_RELEASES_ARCHIVE_URL,
  SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL
)

DATE_RE = re.compile("(January|February|March|April|May|June|July|August|" +
                    "September|October|November|December) ([123]?[0-9]), " +
                    "(20[0-9][0-9])")

IDENTIFIER_RE = re.compile("""\((OIG-[A-Z][A-Z]-[0-9][0-9]-[0-9][0-9])\)""")

utils.run(run) if (__name__ == "__main__") else None
