#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
import bs4
from datetime import datetime
import calendar

def run(options):

  print "## Downloading audits and other reports"
  url = url_for()
  body = utils.download(url)

  doc = BeautifulSoup(body)
  results = doc.select("section")

  for result in results:
    try:
      print "## Downloading year %i " % int(result.get("title"))
    except ValueError:
      continue
    listings = result.div.table.tbody.contents
    for item in listings:
      report_from(item)

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
