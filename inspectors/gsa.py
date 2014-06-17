#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime
import re

# oldest year: 1979

def run(options):
  crawl_index(SEMIANNUAL_REPORTS_URL, options)
  crawl_index(AUDIT_REPORTS_URL, options, True)
  crawl_index(PEER_REVIEW_REPORTS_URL, options)
  crawl_index(MISCELLANEOUS_REPORTS_URL, options)

def crawl_index(base_url, options, is_meta_index=False):
  year_range = inspector.year_range(options)
  max_pages = options.get('pages')
  if max_pages:
    max_pages = int(max_pages)
  page = 1

  only_id = options.get('report_id')

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
    if max_pages and next_page > max_pages:
      done = True

    results = doc.select("div#svPortal dl")
    for result in results:
      if "moreResults" in result.get("class"):
        continue
      if is_meta_index:
        url = "http://www.gsaig.gov" + result.a.get("href")
        crawl_index(url, options, False)
      else:
        report = report_from(result, base_url)
        year = int(report['published_on'][:4])

        if only_id and (report['report_id'] != only_id):
          continue

        if year not in year_range:
          continue

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
    'agency_name': 'General Services Administration'
  }

  link = result.a
  title = link.text
  url = link.get('href')

  date_holders = result.find_all("dt", class_="releaseDate")
  if len(date_holders) > 0:
    published_date = date_holders[0].text
    date = datetime.strptime(published_date, "%B %d, %Y")
  elif title in HARDCODED_DATES:
    # This is an ugly solution, but there's no date information on the web page.
    # The next best solution would be to grab the PDF file and pull the file
    # creation date out of its metadata.
    published_date = HARDCODED_DATES[title]
    date = datetime.strptime(published_date, "%B %d, %Y")
  elif base_url == SEMIANNUAL_REPORTS_URL:
    # get last match
    match = None
    for match in DATE_RE.finditer(title):
      pass
    published_date = match.group(0)
    date = datetime.strptime(published_date, "%B %d, %Y")
  else:
    match = DATE_RE_MM_DD_YY.search(result.text)
    if match:
      published_date = match.group(0)
      date = datetime.strptime(published_date, "%m/%d/%y")
    else:
      raise Exception("Couldn't find date for %s" % title)

  id = ID_RE.search(url).group(1)

  report_type = type_for(base_url)

  js_match = JS_RE.match(url)
  if js_match:
    url = "http://www.gsaig.gov" + js_match.group(1)
  elif url.startswith('/'):
    url = "http://www.gsaig.gov" + url

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
                     "([12][0-9][0-9][0-9])")
DATE_RE_MM_DD_YY = re.compile("[0-9]?[0-9]/[0-9]?[0-9]/[0-9][0-9]")

HARDCODED_DATES = {
  "Hats Off Program Investigative Report": "June 16, 2011",
  "Major Issues from Fiscal Year 2010 Multiple Award Schedule Preaward Audits": "September 26, 2011",
  "Review of Center for Information Security Services FTS": "March 23, 2001",
  "Audit of Procurement of Profesional Services from the FSS Multiple Award Schedules": "July 31, 2003",
  "Special Report: MAS Pricing Practices: Is FSS Observing Regulatory Provisions Regarding Pricing?": "August 24, 2001",
  "Updated Assessment of GSA's Most Serious Challenges": "December 8, 2004",
  "Limited Audit of FSS's Contracting for Services Under Multiple Award Schedule Contracts": "January 9, 2001",
  "Procurement Reform and the Multiple Award Schedule Program": "July 30, 2010",
  "FTS Alert Report": "March 6, 2003",
  "FTS CSC Audit Report": "January 8, 2004",
  "Compendium FTS CSC Audit Report": "December 14, 2004",
  "Compendium FTS CSC Controls Audit Report": "June 14, 2005",
  "Compendium FTS Client Support Center Controls Audit Report": "September 29, 2006",
  "Review of the Federal Acquisition Service's Client Support Center, Southeast Sunbelt Region - A090139-3": "June 4, 2010"
}

utils.run(run) if (__name__ == "__main__") else None
