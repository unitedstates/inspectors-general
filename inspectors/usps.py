#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime


# options:
#   since - date (YYYY-MM-DD) to fetch reports from.
#           defaults to 2 days ago.
#   pages - number of pages to fetch. "all" uses a very high number.
#           defaults to 1.
#   only - limit reports fetched to one or more types, comma-separated. e.g. "audit,testimony"
#          can include:
#             audit - Audit Reports
#             testimony - Congressional Testimony
#             press - Press Releases
#             research - Risk Analysis Research Papers
#             interactive - SARC (Interactive)
#             congress - Semiannual Report to Congress
#          defaults to
#             including audits, reports to Congress, and research
#             excluding press releases, SARC, and testimony to Congress

def run(options):
  pages = options.get('pages', 1)

  for page in range(1, (int(pages) + 1)):
    print "## Downloading page %i" % page
    url = url_for(options, page)
    body = utils.download(url)

    doc = BeautifulSoup(body)
    results = doc.select(".views-row")

    for result in results:
      report = report_from(result)
      inspector.save_report(report)


# extract fields from HTML, return dict
def report_from(result):
  report = {'inspector': 'usps'}

  pieces = result.select("span span")
  report_type = type_for(pieces[0].text.strip())

  if len(pieces) == 3:
    timestamp = pieces[2].text.strip()
    report['%s_id' % report_type] = pieces[1].text.strip()
  elif len(pieces) == 2:
    timestamp = pieces[1].text.strip()

  published_on = datetime.strptime(timestamp, "%m/%d/%Y")

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['year'] = published_on.year

  # if there's only one button, use that URL
  # otherwise, look for "Read Full Report" (could be first or last)
  buttons = result.select("a.apbutton")
  if len(buttons) > 1:
    link = None
    for button in buttons:
      if "Full Report" in button.text:
        link = button['href']
  elif len(buttons) == 1:
    link = buttons[0]['href']
  report['url'] = link

  # get filename, use name as report ID, extension for type
  filename = link.split("/")[-1]
  extension = filename.split(".")[-1]
  report['report_id'] = filename.replace("." + extension, "")
  report['file_type'] = extension

  report['title'] = result.select("h3")[0].text.strip()

  return report

def type_for(original_type):
  original = original_type.lower()
  if "audit" in original:
    return "audit"
  elif "testimony" in original:
    return "testimony"
  elif "press release" in original:
    return "press"
  elif "research" in original:
    return "research"
  elif "sarc" in original:
    return "interactive"
  elif "report to congress":
    return "congress"
  else:
    return "unknown"

def url_for(options, page=1):
  url = "http://www.uspsoig.gov/document-library?"

  since = options.get('since', None)
  if since:
    url += "&field_doc_date_value[value][date]=%s" % since

  only = options.get('only', None)
  if not only:
    only = "audit,congress,research"
  only = only.split(",")
  params = ["field_doc_cat_tid[]=%s" % CATEGORIES[id] for id in only]
  url += "&%s" % str.join("&", params)

  if page > 1:
    url += "&page=%i" % (page - 1)

  return url


CATEGORIES = {
  'audit': '1920',
  'testimony': '1933',
  'press': '1921',
  'research': '1922',
  'interactive': '3487',
  'congress': '1923'
}


utils.run(run)