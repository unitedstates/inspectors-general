#!/usr/bin/env python

from utils import utils, inspector
from datetime import datetime
import re
import logging
from urllib.parse import urljoin, unquote_plus
import os

archive = 1979

INDEX_URLS = [
  "https://www.gsaig.gov/Audit-Reports,-Memos,-and-Oversi",
  "https://www.gsaig.gov/Testimony",
  "https://www.gsaig.gov/FOIA-Reading-Room",
  "https://www.gsaig.gov/Recovery-Act-Reports",
  "https://www.gsaig.gov/Other-Documents",
  "https://www.gsaig.gov/Presentations",
  "https://www.gsaig.gov/Semiannual-Reports-to-the-Congre",
  "https://www.gsaig.gov/Inspection-and-Evaluation-Report",
  "https://www.gsaig.gov/Peer-Review-Reports",
]

def run(options):
  for url in INDEX_URLS:
    crawl_index(url, options)

def crawl_index(base_url, options):
  year_range = inspector.year_range(options, archive)
  max_pages = options.get('pages')
  if max_pages:
    max_pages = int(max_pages)
  page = 1

  only_id = options.get('report_id')

  done = False
  while not done:
    url = url_for(base_url, page)
    doc = utils.beautifulsoup_from_url(url)

    next_page = page + 1
    found_next_page = False
    page_links = doc.select("ul.pagination li a")
    for page_link in page_links:
      if page_link.text == str(next_page):
        found_next_page = True
        break
    if not found_next_page:
      done = True
    if max_pages and next_page > max_pages:
      done = True

    results = doc.select(".views-row")
    if not results and page == 1:
      raise inspector.NoReportsFoundError("Government Services Administration (%s)" % url)
    for result in results:
      report = report_from(result, base_url)
      if not report:
        continue

      year = int(report['published_on'][:4])

      if only_id and (report['report_id'] != only_id):
        continue

      if year not in year_range:
        continue

      inspector.save_report(report)

    page = next_page
    if not done:
      logging.info('Moving to next page (%d)' % page)

def url_for(base_url, page = 1):
  return "%s?page=%d" % (base_url, page - 1)

def report_from(result, base_url):
  report = {
    'inspector': 'gsa',
    'inspector_url': 'https://www.gsaig.gov/',
    'agency': 'gsa',
    'agency_name': 'General Services Administration'
  }

  title_h4 = result.find("div", property="dc:title").h4
  title = inspector.sanitize(title_h4.text)
  if title_h4.a:
    report['landing_url'] = urljoin(base_url, title_h4.a["href"])
  else:
    report['landing_url'] = base_url

  description = result.find("div", class_="field-name-field-description")
  if description:
    report['summary'] = inspector.sanitize(description.text)

  unreleased = False
  url = None
  file_section = result.find("span", class_="file")
  if file_section:
    file_links = file_section.find_all("a")
    if len(file_links) > 1:
      raise Exception("Multiple file links for %s" % title)
    link = file_links[0]
    url = link.get('href')
    url = urljoin(base_url, url)

    if url == "https://www.gsaig.gov/sites/default/files/recovery-reports/FINAL%20TESTIMONY%20FOR%20APRIL%2021.pdf":
      # This testimony is also posted in the testimony section, so we can skip
      # the one posted under recovery reports
      return

    report_id = os.path.splitext(os.path.basename(unquote_plus(url)))[0]
    report_id = re.sub('[-/\\s]+', '-', inspector.sanitize(report_id))
  else:
    unreleased = report['unreleased'] = True
    report_id = re.sub('[-/\\s]+', '-', inspector.sanitize(title))

  published_date_div = result.find("div", class_="field-name-post-date")
  if published_date_div:
    published_date = published_date_div.text
    date = datetime.strptime(published_date, "%B %d, %Y")
  else:
    # get last match
    match = None
    for match in DATE_RE.finditer(title):
      pass
    published_date = match.group(0)
    date = datetime.strptime(published_date, "%B %d, %Y")

  report_type = type_for(base_url)

  report['type'] = report_type
  report['published_on'] = datetime.strftime(date, "%Y-%m-%d")
  if not unreleased:
    report['url'] = url
    if url.lower().endswith(".pdf"):
      report['file_type'] = "pdf"
    elif url.lower().endswith(".doc"):
      report['file_type'] = "doc"
    elif url.lower().endswith(".xls"):
      report['file_type'] = "xls"
    elif url.lower().endswith(".ppt"):
      report['file_type'] = "ppt"
    else:
      raise Exception("Unexpected filetype for %s" % url)
  report['report_id'] = report_id
  report['title'] = title.strip()

  return report

def type_for(base_url):
  if "Audit-Reports" in base_url:
    return "audit"
  if "Testimony" in base_url:
    return "testimony"
  if "FOIA-Reading-Room" in base_url:
    return "other"
  if "Recovery-Act-Reports" in base_url:
    return "audit"
  if "Other-Documents" in base_url:
    return "other"
  if "Presentations" in base_url:
    return "other"
  if "Semiannual-Reports-to-the-Congre" in base_url:
    return "semiannual_report"
  if "Inspection-and-Evaluation-Report" in base_url:
    return "inspection"
  if "Peer-Review-Reports" in base_url:
    return "peer_review"

DATE_RE = re.compile("(January|February|March|April|May|June|July|August|"
                     "September|October|November|December) ([123]?[0-9]), "
                     "([12][0-9][0-9][0-9])")

utils.run(run) if (__name__ == "__main__") else None
