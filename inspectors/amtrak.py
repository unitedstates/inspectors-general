#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime

archive = 2006

INDEX_URLS = [
  "https://www.amtrakoig.gov/reports/all-audits",
  "https://www.amtrakoig.gov/reports/all-investigations",
  "https://www.amtrakoig.gov/reading-room/all-documents",
]

def run(options):
  year_range = inspector.year_range(options, archive)

  for index in INDEX_URLS:
    report_count = 0
    for year in year_range:
      url = url_for(options, index, year)
      body = utils.download(url)

      doc = BeautifulSoup(body)

      results = doc.select("div.view-content div.views-row")
      for result in results:
        report = report_from(result)
        inspector.save_report(report)
        report_count = report_count + 1

    if report_count == 0:
      raise inspector.NoReportsFoundError("Amtrak (%s)" % index.split("/")[-1])

def url_for(options, index, year=None):
  if year:
    year = str(year)
  else:
    year = ''
  return "%s?sort_by=field_issue_date_value&field_issue_date_value[value][year]=%s&items_per_page=All" % (index, year)

def report_from(result):
  report = {
    'inspector': 'amtrak',
    'inspector_url': 'http://amtrakoig.gov/',
    'agency': 'amtrak',
    'agency_name': 'Amtrak'
  }
  title = result.select("div.details h3")[0].text.strip()
  url = result.select("div.access div.link a")[0].get("href")
  issued, category = result.select("div.details div.date")[0].text.split("|", maxsplit=2)
  category = category.strip()
  tracking = result.select("div.access div.track-num")[0].text.strip()

  published_on = datetime.strptime(issued.strip(), '%B %d, %Y')
  report_type = type_for(category)
  report_id = tracking.strip()

  if report_id and title.lower().startswith('closeout'):
    report_id = report_id + "_closeout"
  if report_id == "008-2015":
    # This tracking number appears to be used for two different projects
    if "management_challenges" in url:
      report_id = "008-2015-challenges"
    else:
      report_id = "008-2015-msa"

  if not report_id:
    report_id = url[url.rfind('/') + 1 : url.rfind('.')]

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['url'] = url
  report['report_id'] = report_id
  report['title'] = title

  return report

def type_for(category):
  original = category.lower()
  if "audit" in original:
    return "audit"
  if "testimony" in original:
    return "testimony"
  if "press release" in original:
    return "press"
  return "other"

utils.run(run) if (__name__ == "__main__") else None
