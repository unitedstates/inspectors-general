#!/usr/bin/env python

import datetime
from urllib.parse import urljoin, urlencode
import re
import os
import logging
from bs4 import BeautifulSoup
from utils import utils, inspector

# http://www.oig.dot.gov/
# oldest year: 1996

#
# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated.
#            e.g. "A,IN". Defaults to all topics.
#
#          A    - Audits
#          IN   - Investigations
#          T    - Testimony
#          C    - Correspondence
#          R    - Recovery Act
#          SA   - Semiannual Reports

# Notes to IG's web team:
#   - All report types are the same (some report links just link to other agency's homepages)
#   - No easy way to distinguish work product from preliminary and intermediary announcements.
#   - Add report ids to all pages in a consistent way
#   - From a report's landing page, no way to see what oversight area or sub-agency a report belongs to.
#   - Read https://github.com/unitedstates/inspectors-general/pull/50 for more details.

TOPIC_TO_URL = {
  "A": "http://www.oig.dot.gov/audits",
  "IN": "http://www.oig.dot.gov/investigations",
  "T": "http://www.oig.dot.gov/testimony",
  "C": "http://www.oig.dot.gov/correspondence",
  "R": "http://www.oig.dot.gov/recovery",
  "SA": "http://www.oig.dot.gov/semiannual-reports",
}

TYPES_WITHOUT_REPORTS = [
  'New Audit Announcements',
]

UNRELEASED_REPORT_TYPES = [
  'Investigations',
  'Audit Reports',
]

UNRELEASED_REPORT_IDS = [
  "CC-2000-290",
  "AV-2009-066"
]

LANDING_URLS_TO_REPORT_LINKS = {
  "http://www.oig.dot.gov/library-item/5235": "http://www.osc.gov/FY2010/Scanned/10-07%20DI-08-2225/DI-08-2225%20Agency%20Report%20Part%201%20(Revised).PDF",
}

BASE_REPORT_PAGE_URL = BASE_REPORT_URL = "http://www.oig.dot.gov/"

def run(options):
  year_range = inspector.year_range(options)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  for topic in topics:
    year_urls = urls_for(year_range, topic)
    for year_url in year_urls:
      body = utils.download(year_url)

      doc = BeautifulSoup(body)
      results = doc.select(".item-list ul li")

      for result in results:
        report = report_from(result, year_range, topic)
        if report:
          inspector.save_report(report)

def urls_for(year_range, topic):
  topic_url = TOPIC_TO_URL[topic]
  return ["%s?date_filter[value][year]=%s" % (topic_url, year) for year in year_range]

def report_from(result, year_range, topic):
  published_date_text = result.select('.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%m.%d.%Y")

  landing_url_link = result.select('a')[0]
  landing_url_relative = landing_url_link['href']
  title = landing_url_link.text
  landing_url = urljoin(BASE_REPORT_PAGE_URL, landing_url_relative)

  if published_on.year not in year_range:
    # Some reports come in from the 'Most Popular' section of the page and that
    # section does not obey the year filters
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("### Processing report %s" % landing_url)

  report_page_body = utils.download(landing_url)
  report_page = BeautifulSoup(report_page_body)
  summary = report_page.select(".summary-body")[0].text.strip()

  report_type = report_page.select("#content-wrapper div h2")[0].text

  try:
    report_id = report_page.select("div.project-id")[0].text
    report_id = report_id.replace("Project ID: ", "")  # Strip out the text
  except IndexError:
    report_id = None

  unreleased = False
  try:
    report_url = urljoin(BASE_REPORT_URL, report_page.select(".download-pdf a")[0]['href'])
  except IndexError:
    try:
      report_url = urljoin(BASE_REPORT_URL, report_page.select("div.item-link a")[0]['href'])
    except IndexError as exc:
      if report_type in TYPES_WITHOUT_REPORTS:
        # Some types just don't have reports(Announcements), ignore them
        return
      elif (
          'For Official Use Only' in summary
          or report_type in UNRELEASED_REPORT_TYPES
          or report_id in UNRELEASED_REPORT_IDS
        ):
        unreleased = True
        report_url = None
        if not report_id:
          report_id = landing_url.split("/")[-1]
      elif landing_url in LANDING_URLS_TO_REPORT_LINKS:
        report_url = LANDING_URLS_TO_REPORT_LINKS[landing_url]
      else:
        raise exc

  # Try to pull the filename for a report_id
  if not report_id:
    report_id = os.path.splitext(os.path.basename(report_url))[0]

  # Fall back to using the id from the landing_url
  if not report_id:
    report_id = landing_url.split("/")[-1]

  # Some investigations provide a report link, but they are just links to other
  # sites. Mark these as unreleased.
  # Ex. http://www.oig.dot.gov/library-item/5085
  if report_url:
    report_extension = os.path.splitext(os.path.basename(report_url))[1]
    if report_type == 'Investigations' and not report_extension:
      unreleased = True
      report_url = None

  # The DOT has lots of links to reports from other agencies. Ignore them.
  if report_url and BASE_REPORT_URL not in report_url:
    logging.debug("### Skipping report %s (not DOT)" % landing_url)
    return

  # These are just announcements, not real reports
  if "Audit Initiated" in title:
    return

  # Check for related reports. This will help us group related reports later.
  related_reports = [
    urljoin(BASE_REPORT_URL, link['href'])
    for link
    in report_page.select(".view-related-library-items li a")
  ]

  report = {
    'inspector': 'dot',
    'inspector_url': 'https://www.oig.dot.gov',
    'agency': 'dot',
    'agency_name': 'Department of Transportation',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
    'landing_url': landing_url,
    'summary': summary,
    'topic': topic,
    'type': report_type,
  }
  if unreleased:
    report['unreleased'] = unreleased
  if related_reports:
    report['related_reports'] = related_reports
  return report

utils.run(run) if (__name__ == "__main__") else None
