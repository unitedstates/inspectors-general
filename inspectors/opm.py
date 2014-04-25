#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
import bs4
from datetime import datetime
import calendar

#  Note: reports are only scraped from /our-inspector-general/reports/
#  I think this is mostly just audit reports (other reports are scattered
#  around the website

#  options
#    --since=[year] fetches all reports from that year to now

def run(options):

  this_year = datetime.now().year
  since = int(options.get('since', this_year))
  if since > this_year:
    since = this_year
  if since != this_year:
    print "## Downloading reports from %i to %i" % (since, this_year)
  else:
    print "## Downloading reports from this year (%i)" % this_year

  url = url_for()
  body = utils.download(url)

  doc = BeautifulSoup(body)
  results = doc.select("section")

  for result in results:
    try:
      year = int(result.get("title"))
      # check that the fetched year is in the range
      if year not in range (since, this_year + 1):
        continue
      print "## Downloading year %i " % year
    except ValueError:
      continue
    # gets each table entry and sends generates a report from it
    listings = result.div.table.tbody.contents
    for item in listings:
      if type(item) is not bs4.element.Tag:
        continue
      report_from(item)

#  really only here for symbolic purposes
def url_for():
  return "http://www.opm.gov/our-inspector-general/reports/"

#  generates the report item from a table item
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
  
  if 'audit' not in report['name'].lower():
    report['type'] = 'other'

  # if the document doesn't have a listed id - use hash of name
  raw_id = str(hash(report['name']))
  try:
    raw_id = item.find_all('td')[1].contents[0]
    if type(raw_id) is bs4.element.Tag:
      while raw_id.span:
        raw_id = raw_id.span
      raw_id = raw_id.string
  except IndexError:
    pass
  report['report_id'] = raw_id

  inspector.save_report(report)


def find_month_num(month):
  for i in range(len(calendar.month_name)):
    if month == calendar.month_name[i]:
      return i
  return -1


utils.run(run)
