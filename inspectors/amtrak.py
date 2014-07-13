#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# oldest year: 2006

# options:
#   --pages: limit the scraper to a certain number of pages

def run(options):
  year_range = inspector.year_range(options)

  max_pages = options.get('pages', None)
  if max_pages:
    max_pages = int(max_pages)

  for year in year_range:
    page = 1
    done = False
    while not done:
      url = url_for(options, page, year)
      body = utils.download(url)

      doc = BeautifulSoup(body)

      next_page = page + 1
      found_next_page = False
      page_links = doc.select("li.pager-item a.active")
      for page_link in page_links:
        if page_link.text == str(next_page):
          found_next_page = True
          break
      if not found_next_page:
        done = True
      if max_pages and (next_page > max_pages):
        done = True

      results = doc.select("table.views-table > tbody > tr")
      for result in results:
        report = report_from(result)
        inspector.save_report(report)

      page = next_page
      if not done:
        logging.info('Moving to next page (%d)' % page)

def url_for(options, page = 1, year=None):
  if year:
    year = str(year)
  else:
    year = ''
  return "http://www.amtrakoig.gov/reading-room?date_filter[value][year]=%s&term_node_tid_depth=%s&page=%d" % (year, 'All', page - 1)

def report_from(result):
  report = {
    'inspector': 'amtrak',
    'inspector_url': 'http://amtrakoig.gov/',
    'agency': 'amtrak',
    'agency_name': 'Amtrak'
  }
  link = result.find_all("td", class_="views-field-phpcode-2")[0].a
  title = link.text
  url = link.get('href')
  category = result.find_all("td", class_="views-field-name")[0].text
  issued = result.find_all("td", class_="views-field-field-issue-date-value")[0].text
  tracking = result.find_all("td", class_="views-field-field-tracking-value")[0].text
  total_views = result.find_all("td", class_="views-field-totalcount")[0].text

  published_on = datetime.strptime(issued.strip(), '%m/%d/%Y')
  report_type = type_for(category)
  report_id = tracking.strip()
  if not report_id:
    report_id = url[url.rfind('/') + 1 : url.rfind('.')]

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['url'] = url
  report['report_id'] = report_id
  report['title'] = title.strip()

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
