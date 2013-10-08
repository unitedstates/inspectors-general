#!/usr/bin/env python

import utils

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

# import PyQuery

def run(options):
  print utils.download("http://www.uspsoig.gov/document-library")



utils.run(run)