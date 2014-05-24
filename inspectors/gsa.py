#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime
import re

def run(options):
  crawl_index(SEMIANNUAL_REPORTS_URL, options)
  crawl_index(AUDIT_REPORTS_URL, options, True)
  crawl_index(PEER_REVIEW_REPORTS_URL, options)
  crawl_index(MISCELLANEOUS_REPORTS_URL, options)

def crawl_index(base_url, options, is_meta_index=False):
  max_pages = int(options.get('pages', 1))
  page = 1
  done = False
  while not done:
    url = url_for(base_url, page)
    body = utils.download(url)

    doc = BeautifulSoup(body)

    next_page = page + 1
    found_next_page = False
    page_links = doc.select("dl.moreResults a")
    for page_link in page_links:
      if page_link.text == str(next_page):
        found_next_page = True
        break
    if not found_next_page:
      done = True
    if next_page > max_pages:
      done = True

    results = doc.select("div#svPortal dl")
    for result in results:
      if is_meta_index:
        url = "http://www.gsaig.gov" + result.a.get("href")
        crawl_index(url, options, False)
      else:
        report = report_from(result, base_url)
        inspector.save_report(report)

    page = next_page
    if not done:
      print('Moving to next page (%d)' % page)

def url_for(base_url, page = 1):
  return "%s?startRow=%d" % (base_url, page * 10 - 9)

def report_from(result, base_url):
  report = {
    'inspector': 'gsa',
    'inspector_url': 'http://gsaig.gov/',
    'agency': 'gsa',
    'agency_name': 'Amtrak'
  }

  link = result.a
  title = link.text
  url = link.get('href')
  date_holders = result.find_all("dt", class_="releaseDate")
  if len(date_holders) > 0:
    published_date = date_holders[0].text
  else:
    if title == "Hats Off Program Investigative Report":
      published_date = "June 16, 2011"
    elif base_url == SEMIANNUAL_REPORTS_URL:
      # get last match
      for match in DATE_RE.finditer(title):
        pass
      published_date = match.group(0)
  date = datetime.strptime(published_date, "%B %d, %Y")

  id = ID_RE.search(url).group(1)
  report_type = type_for(base_url)

  js_match = JS_RE.match(url)
  if js_match:
    url = "http://www.gsaig.gov" + js_match.group(1)

  report['type'] = report_type
  report['published_on'] = datetime.strftime(date, "%Y-%m-%d")
  report['url'] = url
  report['report_id'] = id
  report['title'] = title.strip()
  report['file_type'] = 'pdf'

  return report

def type_for(base_url):
  if base_url.find('special-reports') != -1:
    return "audit"
  if base_url.find('audit-reports') != -1:
    return "audit"
  return "other"

SEMIANNUAL_REPORTS_URL = "http://www.gsaig.gov/index.cfm/oig-reports/semiannual-reports-to-the-congress/"
AUDIT_REPORTS_URL = "http://www.gsaig.gov/index.cfm/oig-reports/audit-reports/"
PEER_REVIEW_REPORTS_URL = "http://www.gsaig.gov/index.cfm/oig-reports/peer-review-reports/"
MISCELLANEOUS_REPORTS_URL = "http://www.gsaig.gov/index.cfm/oig-reports/miscellaneous-reports/"

ID_RE = re.compile("LinkServID=([-0-9A-F]*)&showMeta=")
JS_RE = re.compile("""javascript:newWin=window.open\('/(\?LinkServID=([-0-9A-F]*)&showMeta=0)','NewWin[0-9]*'\);newWin.focus\(\);void\(0\)""")
DATE_RE = re.compile("(January|February|March|April|May|June|July|August|" +
                     "September|October|November|December) ([123]?[0-9]), " +
                     "(20[0-9][0-9])")

utils.run(run) if (__name__ == "__main__") else None
