#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# http://www.oig.doc.gov/Pages/Audits-Evaluations.aspx?YearStart=01/01/1996&YearEnd=12/31/2014
archive = 1996

# options:
#   standard since/year options for a year range to fetch from.
#
#   topics - limit reports fetched to one or more topics, comma-separated, which
#            correspond to the topics defined on the site. For example:
#            'A,I'
#            Defaults to all topics.
#
#            A    - Audits and Evaluations
#            I    - Investigations
#            C    - Correspondence
#            AI   - Audits Initiated
#            T    - Testimony

# Notes for IG's web team:
#

TOPIC_TO_URL_SLUG = {
  "A": 'Audits-Evaluations',
  "I": 'Investigations',
  "C": 'Correspondence',
  "AI": 'Audits-Initiated',
  "T": 'Testimony',
}
TYPE_MAP = {
  "A": "audit",
  "I": "investigation",
  "C": "congress",
  "AI": "audit",
  "T": "testimony",
}
BASE_TOPIC_URL = "http://www.oig.doc.gov/Pages/{}.aspx"

all_reports = {}

def run(options):
  year_range = inspector.year_range(options, archive)

  topics = options.get('topics')
  if topics:
    topics = topics.split(",")
  else:
    topics = TOPIC_TO_URL_SLUG.keys()

  for topic in topics:
    extract_reports_for_topic(topic, year_range)

  for report in all_reports.values():
    inspector.save_report(report)

def extract_reports_for_topic(topic, year_range):
  global all_reports

  topic_url = url_for(year_range).format(TOPIC_TO_URL_SLUG[topic])

  topic_page = utils.beautifulsoup_from_url(topic_url)
  results = topic_page.select("div.row")
  if not results:
    temp_text = topic_page.select("div.item")[0].text
    if temp_text.find("No items available for ") == -1:
      raise inspector.NoReportsFoundError("Department of Commerce (%s)" % topic)
  for result in results:
    report = report_from(result, topic, topic_url, year_range)
    if report:
      key = (report["report_id"], report["title"])
      if key in all_reports:
        all_reports[key]["type"] = all_reports[key]["type"] + ", " + \
                report["type"]
      else:
        all_reports[key] = report

def url_for(year_range):
  return "%s?YearStart=01/01/%s&YearEnd=12/31/%s" % (BASE_TOPIC_URL, year_range[0], year_range[-1])


def report_from(result, topic, topic_url, year_range):
  published_on_text = result.select("div.row-date")[0].text
  published_on = datetime.datetime.strptime(published_on_text, '%m.%d.%Y')
  report_type = TYPE_MAP[topic]

  title = result.select("div.row-title")[0].text.strip()

  if title == "OIG-15-026-A-Abstract":
    # This row is a duplicate of "USPTO Needs to Strengthen Patent Quality
    # Assurance Practices," and there isn't a link.
    return

  unreleased = False
  if "not publically released" in title:
    unreleased = True

  if unreleased:
    report_url = None
    try:
      report_id = title.split(":")[1].split("(")[0]
    except IndexError:
      # Some reports don't have report ids listed. Make a slug from the title and date
      report_id = "{}-{}".format(published_on_text, "-".join(title.split()))[:50]
    landing_url = topic_url  # There are not dedicated landing pages for unreleased reports :(
  else:
    link = result.select("a")[0]
    landing_url = link.get('href')

    if landing_url == "http://www.oig.doc.gov/Pages/Letter-to-Sen-Snowe-re-Northeast-Fisheries-Science-Center-2009.02.09.aspx":
      # Duplicate of http://www.oig.doc.gov/Pages/Letter-to-Sens-Snowe-Collins-Kennedy-Kerry-re-Investigation-Work-Scientific-Methods-of-NMFS-NFSC-2009.02.26.aspx
      return

    landing_page = utils.beautifulsoup_from_url(landing_url)
    try:
      if landing_url.endswith("/Top-Management-Challenges-FY-2011.aspx") or \
                landing_url.endswith("/Observations-and-Address-Listers-" \
                "Reports-Provide-Serious-Indications-That-Important-Address-" \
                "Canvassing.aspx"):
        # Testimony on these landing pages already show up elsewhere, so we pick
        # the report instead
        report_url_relative = landing_page.select("div.oig_Publications a")\
            [-2].get('href')
      else:
        report_url_relative = landing_page.select("div.oig_Publications a")\
            [-1].get('href')
    except IndexError:
      # If there is no linked report, this page is the report. We know that
      # these are not unreleased reports or we would have caught them above
      # based on the title.
      unreleased = True
      report_url = None
    else:
      report_url = urljoin(topic_url, report_url_relative)

    missing = False
    if report_url == "http://www.oig.doc.gov/OIGPublications/Announcement-DOC-IPERA.pdf":
      missing = True
      unreleased = True

    if report_url:
      report_filename = report_url.split("/")[-1]
      report_id, extension = os.path.splitext(report_filename)
    else:
      report_id = "{}-{}".format(published_on_text, "-".join(title.split()))[:50]

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  file_type = None
  # urllib.parse has trouble parsing the extension for some urls.
  # Ex: http://www.oig.doc.gov/Pages/NIST-Grant-Recipient-Sentenced-for-Grant-Fraud;-Civil-Suit-Filed.aspx
  if report_url and report_url.endswith(".aspx"):
    file_type = "aspx"
  # Some off-site links (i.e. to the FBI) don't have obvious file extensions
  elif (report_url and (report_url.startswith("http://www.fbi.gov/") or
        report_url.startswith("http://www.justice.gov/")) and
        not os.path.splitext(os.path.basename(report_url))[1]):
    file_type = "html"

  result = {
    'inspector': 'commerce',
    'inspector_url': 'http://www.oig.doc.gov',
    'agency': 'commerce',
    'agency_name': 'Department of Commerce',
    'report_id': report_id,
    'type': report_type,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if landing_url:
    result['landing_url'] = landing_url
  if unreleased:
    result['unreleased'] = unreleased
  if missing:
    result['missing'] = missing
  if file_type:
    result['file_type'] = file_type
  return result

utils.run(run) if (__name__ == "__main__") else None
