#!/usr/bin/env python

import utils
from pyquery import PyQuery

# options:
#   since - date (YYYY-MM-DD) to fetch reports from, or "all" to go back indefinitely.
#           defaults to 2 days ago.
#   only - limit reports fetched to one or more types, comma-separated. e.g. "audits,testimony"
#          can include:
#             audits - Audit Reports
#             testimony - Congressional Testimony
#             press - Press Releases
#             research - Risk Analysis Research Papers
#             sarc - SARC (Interactive)
#             congress - Semiannual Report to Congress
#          defaults to None (will fetch all reports)

def run(options):
  url = "http://www.uspsoig.gov/document-library?"

  since = options.get('since', None)
  if since:
    url += "&field_doc_date_value[value][date]=%s" % since

  only = options.get('only', None)
  if only:
    only = only.split(",")
    params = ["field_doc_cat_tid[]=%s" % CATEGORIES[id] for id in only]
    url += "&%s" % str.join("&", params)

  print url

  body = utils.download(url)
  doc = PyQuery(body)


  titles = doc(".views-row div h3")
  for title in titles:
    print title.text

CATEGORIES = {
  'audits': '1920',
  'testimony': '1933',
  'press': '1921',
  'research': '1922',
  'sarc': '3487',
  'congress': '1923'
}

utils.run(run)