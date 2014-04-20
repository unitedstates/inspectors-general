#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
import bs4
from datetime import datetime
import calendar

# This script's "run" function will be run.
# You can do anything you want that eventually results in calling:
#
#   inspector.save_report(report)
#
# Where report is a dict with the following required fields:
#
#   inspector: the handle you chose for the IG, e.g. "usps"
#   agency: the agency the report relates to.
#           This can be the same value as the inspector field, but it
#           may differ -- some IGs monitor multiple agencies.
#   report_id: a unique ID for the report
#   title: title of report
#   url: link to report
#   type: "report" (or some other class of document, if it makes sense to distinguish)
#   published_on: date of publication
#   year: year of publication
#   file_type: 'pdf' or other file extension
#
# Any additional fields are fine, and will be kept.

def run(options):

  # Suggested flow, for an IG which paginates results.
  print "## Downloading audits listing"
  url = url_for()
  body = utils.download(url)

  doc = BeautifulSoup(body)
  results = doc.select("section")
  print "## Downloading year %i " % int(results[0].get("title"))
  listings = results[0].div.table.tbody.contents
  for item in listings:
    if type(item) is not bs4.element.Tag:
      continue
    report_from(item)

  # for result in results:
  #   try:
  #     print "## Downloading year %i " % int(result.get("title"))
  #   except ValueError:
  #     continue
  #   listings = result.div.table.tbody.contents
  #   for item in listings:
  #     report_from(item)

def url_for():
  return "http://www.opm.gov/our-inspector-general/reports/"

def report_from(item):
  report = {
    'inspector': 'opm',
    'inspector_url': 'http://www.opm.gov/our-inspector-general/',
    'agency': 'opm',
    'agency_name': 'U.S. Office of Personnel Management',
    'type': 'audit',
    'file_type': 'pdf'
  }
  raw_date = item.th.contents[0].split(" ")
  month = str(find_month_num(raw_date[0]))
  day = raw_date[1].replace(",", "")
  year = raw_date[2]

  report['published_on'] = year + "-" + month + "-" + day
  report['year'] = year

  raw_link = item.find_all('td')[0].a
  report['url'] = 'http://www.opm.gov' + raw_link.get('href')
  report['name'] = raw_link.string

  raw_id = item.find_all('td')[1].contents[0]
  while raw_id.span:
    raw_id = raw_id.span
  report['report_id'] = raw_id.string

  inspector.save_report(report)


def find_month_num(month):
  for i in range(len(calendar.month_name)):
    if month == calendar.month_name[i]:
      return i
  return -1


utils.run(run)
