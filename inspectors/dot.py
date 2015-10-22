#!/usr/bin/env python

import datetime
from urllib.parse import urljoin
import os
import logging
from utils import utils, inspector

# https://www.oig.dot.gov/
archive = 1996


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
  "A": "https://www.oig.dot.gov/audits",
  "IN": "https://www.oig.dot.gov/investigations",
  "T": "https://www.oig.dot.gov/testimony",
  "C": "https://www.oig.dot.gov/correspondence",
  "R": "https://www.oig.dot.gov/recovery",
  "SA": "https://www.oig.dot.gov/semiannual-reports",
}

TYPES_WITHOUT_REPORTS = [
  'New Audit Announcements',
  'Testimony',
  'Press Release'
]

UNRELEASED_REPORT_TYPES = [
  'Audit Reports',
  'Correspondence',
  'Investigations',
]

UNRELEASED_REPORT_IDS = [
  "30277"
]

LANDING_URLS_TO_REPORT_LINKS = {
  "https://www.oig.dot.gov/library-item/5235": "https://www.osc.gov/FY2010/Scanned/10-07%20DI-08-2225/DI-08-2225%20Agency%20Report%20Part%201%20(Revised).PDF",
}

BASE_REPORT_PAGE_URL = BASE_REPORT_URL = "https://www.oig.dot.gov/"

def run(options):
  year_range = inspector.year_range(options, archive)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL.keys()

  all_reports = {}

  for topic in topics:
    year_urls = urls_for(year_range, topic)
    for year_url in year_urls:
      logging.debug("Scraping %s" % year_url)
      doc = utils.beautifulsoup_from_url(year_url)

      if not doc.select(".view-business-areas"):
        raise inspector.NoReportsFoundError("DOT (%s)" % topic)

      results = doc.select(".view-business-areas .views-row")
      for result in results:
        report = report_from(result, year_range, topic, options)
        if report:
          report_id = report["report_id"]
          if report_id in all_reports:
            all_reports[report_id]["topic"] = all_reports[report_id]["topic"] \
                + ", " + topic
          else:
            all_reports[report_id] = report

  for report in all_reports.values():
    inspector.save_report(report)

def urls_for(year_range, topic):
  topic_url = TOPIC_TO_URL[topic]
  return ["%s?date_filter[value][year]=%s" % (topic_url, year) for year in year_range]

def report_from(result, year_range, topic, options):
  published_date_text = result.select('.date-display-single')[0].text
  published_on = datetime.datetime.strptime(published_date_text, "%m.%d.%Y")

  landing_url_link = result.select('a')[0]
  landing_url_relative = landing_url_link['href']

  # scan to see if we're limiting to a single report_id in dev
  initial_report_id = landing_url_relative.split("/")[-1]
  only_report_id = options.get('report_id')
  if only_report_id and (initial_report_id != only_report_id):
    logging.debug("[%s] Skipping, not the requested report" % initial_report_id)
    return

  title = landing_url_link.text
  landing_url = urljoin(BASE_REPORT_PAGE_URL, landing_url_relative)

  if published_on.year not in year_range:
    # Some reports come in from the 'Most Popular' section of the page and that
    # section does not obey the year filters
    logging.debug("[%s] Skipping, not in requested range." % landing_url)
    return

  logging.debug("### Processing report %s" % landing_url)

  report_page = utils.beautifulsoup_from_url(landing_url)

  # take an expansive view of the 'summary' -
  #   landing page title, and any paragraphs with summary text
  summary = report_page.select(".node-library-item")[0].text.strip()

  # the text from the last link in the breadcrumb
  crumbs = report_page.select("nav.breadcrumb ol li")
  if len(crumbs) == 1:
    report_type = "Press Release"
  else:
    report_type = report_page.select("nav.breadcrumb ol li")[1].select("a")[0].text

  # should always work?
  report_id = landing_url.split("/")[-1]

  unreleased = False
  try:
    report_url = urljoin(BASE_REPORT_URL, report_page.select(".download-pdf a")[0]['href'])
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
    elif landing_url in LANDING_URLS_TO_REPORT_LINKS:
      report_url = LANDING_URLS_TO_REPORT_LINKS[landing_url]
    else:
      raise exc

  # Some investigations provide a report link, but they are just links to other
  # sites. Mark these as unreleased.
  # Ex. https://www.oig.dot.gov/library-item/5085
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
