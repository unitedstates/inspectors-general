#!/usr/bin/env python

import datetime
import logging
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.cncsoig.gov
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#

REPORTS_URLS = [
  ('http://www.cncsoig.gov/news/semi-annual-reports', 'semiannual_report'),
  ('http://www.cncsoig.gov/news/audit-reports', 'audit'),
  ('http://www.cncsoig.gov/operations/investigations', 'investigation'),
  ('http://www.cncsoig.gov/news/archive', 'investigation'),
  ('http://www.cncsoig.gov/news/closed-cases', 'case'),
]

# some hardcoded fields for a single peer review
PEER_REVIEW_2012 = {
  "report_id": "fbrinvestpeer2012_1",
  "landing_url": "http://www.cncsoig.gov/2012-investigations-peer-review",
  "url": "http://www.cncsoig.gov/sites/default/files/fbrinvestpeer2012_1.pdf",
  "published_on": datetime.datetime(2012, 9, 19),
  "title": "Quality Assessment Review of the Investigative Operations of the Office of Inspector General for the Corporation for National and Community Service Investigative Operations",
  "summary": "Review of the system of internal safeguards and management procedures for the investigative functions of the Office of Inspector General (OIG) for the Corporation for National and Community Service (CNCS) in effect during the period May 1, 2011, through May 18, 2012. Our review was conducted in conformity with the Quality Standards for Investigations and the Quality Assessment Review Guidelines for Investigative Operations of Federal Offices of Inspector General established by the Council of the Inspectors General on Integrity and Efficiency (CIGIE) and the Attorney General's Guidelines for Office of Inspectors General with Statutory Law Enforcement Authority, as applicable."
}

def run(options):
  year_range = inspector.year_range(options, archive)

  last_page = options.get("end")
  start = int(options.get("start", 1))

  # Pull the reports
  for (reports_page, report_type) in REPORTS_URLS:

    page = start
    last_page = options.get("end") # reset for each area
    while True:
      url = url_for(reports_page, page)
      doc = BeautifulSoup(utils.download(url))

      if last_page is None:
        last_page = last_page_from(doc)

      if report_type == "case":
        results = doc.select("div#main div.grayBox2")
      else:
        results = doc.select("div#main div.whiteBox")

      if results:
        for result in results:
          report = report_from(result, reports_page, report_type, year_range)
          if report:
            inspector.save_report(report)
      elif report_type != "case":
        raise inspector.NoReportsFoundError("CNCS (%s)" % url)
      # closed cases have broken pagination (p6, 7, 8 missing) so ignore
      else:
        pass

      if int(page) >= int(last_page):
        break
      else:
        page += 1

  # one hardcoded peer review, just always do it
  inspector.save_report(do_peer_review())

def url_for(base, page):
  return "%s?p=%i" % (base, page)

def last_page_from(doc):
  last = doc.select("#pager a#last")
  if len(last) == 0:
    return 1
  else:
    last = last[0]
    return int(last['href'].split("=")[-1])

def report_from(result, reports_page, report_type, year_range):
  unreleased = False
  summary = None
  landing_url = None
  estimated_date = False

  # audits have some data, but link to landing page for summary and URL
  if report_type == "audit":
    landing_a = result.select(".cell3 a")[0]
    landing_url = urljoin(reports_page, landing_a['href'])
    long_title = landing_a.text.strip()

    # http://www.cncsoig.gov/news-entry/97-09 and
    # http://www.cncsoig.gov/news-entry/97-09-0 are duplicates of each other
    if landing_url == "http://www.cncsoig.gov/news-entry/97-09-0":
      return

    # PDF URL and summary are on the report's landing page
    report_url, summary, title = extract_from_release_page(landing_url)
    if not report_url:
      unreleased = True

    if not title:
      title = long_title

    # the report PDF URL can be pulled from the comments
    # we're ignoring this since we're going to the landing page anyhow.
    # re.search("href=\"(/sites/default/files/.*?)\">GO", str(result))

    report_id = result.select(".cell1")[0].text.strip()
    stamp = result.select(".cell2")[0].text.strip()
    published_on = datetime.datetime.strptime(stamp, "%m.%d.%Y")

  elif report_type == "investigation":
    stamp = result.select(".cell2")[0].text.strip()
    published_on = datetime.datetime.strptime(stamp, "%Y-%m-%d")
    title = result.select(".cell3 p")[0].text.strip()

    report_url = result.select(".cell3 a")[0]['href']
    report_url = urljoin(reports_page, report_url)
    report_id = os.path.splitext(report_url.split("/")[-1])[0]

  elif report_type == "semiannual_report":
    report_url = result.select(".cell4 a")[0]['href']
    report_url = urljoin(reports_page, report_url)
    report_id = os.path.splitext(report_url.split("/")[-1])[0]

    stamps = result.select(".cell2")[0].text.strip().split()
    # the agency can mess up the date order
    if stamps[2] == "09.30.2013":
      stamp = stamps[0]
    else:
      stamp = stamps[2]
    published_on = datetime.datetime.strptime(stamp, "%m.%d.%Y")

    title = str.join(" ", stamps)


  elif report_type == "case":
    report_type = "investigation"
    title = result.select("div")[0].text

    id_text = None
    summary = ""
    for p in result.select("p"):
      text = p.text.strip()
      summary += text + "\n\n"
      if text.lower().strip("-").strip().startswith("case id"):
        id_text = text
    summary = summary.strip()
    if not id_text:
      for div in result.select("div"):
        text = div.text.strip()
        if text.lower().strip("-").strip().startswith("case id"):
          id_text = text
    if not id_text:
      raise Exception("Could not find Case ID for an investigation\n%s" % \
                        result.text)

    #note that some cases have more than one id. We are taking only the last id.
    report_id = re.sub(r'\([^)]*\)','',id_text).strip().split(" ")[-1]

    landing_url = reports_page
    unreleased = True
    report_url = None

    year = int(report_id.split("-")[0])
    published_on = datetime.date(year, 1, 1)
    estimated_date = True

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'cncs',
    'inspector_url': 'http://www.cncsoig.gov',
    'agency': 'cncs',
    'agency_name': 'Corporation for National and Community Service',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'type': report_type,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),  # Date of publication
  }

  if unreleased:
    report['unreleased'] = True

  if summary:
    report['summary'] = summary

  if landing_url:
    report['landing_url'] = landing_url

  if estimated_date:
    report['estimated_date'] = estimated_date

  return report

def do_peer_review():
  return {
    'inspector': 'cncs',
    'inspector_url': 'http://www.cncsoig.gov',
    'agency': 'cncs',
    'agency_name': 'Corporation for National and Community Service',
    'type': 'peer_review',
    'report_id': PEER_REVIEW_2012['report_id'],
    'landing_url': PEER_REVIEW_2012['landing_url'],
    'url': PEER_REVIEW_2012['url'],
    'title': PEER_REVIEW_2012['title'],
    'summary': PEER_REVIEW_2012['summary'],
    'published_on': datetime.datetime.strftime(PEER_REVIEW_2012['published_on'], "%Y-%m-%d"),
  }

# gets URL and summary from a report's landing page
def extract_from_release_page(landing_url):
  doc = BeautifulSoup(utils.download(landing_url))
  main = doc.select("#main #lefSide")[0]

  url_elem = main.select("div")[2].select("a")
  if url_elem:
    url = urljoin(landing_url, url_elem[0]['href'])
  else:
    url = None

  summary = ""
  for p in main.select("p"):
    summary += p.text + "\n\n"

  # will only be used if the title isn't present on the listing
  title = main.select("h2")[0].text.strip()

  return (url, summary.strip(), title)

utils.run(run) if (__name__ == "__main__") else None
