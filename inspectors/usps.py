#!/usr/bin/python

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

import utils

def run(options):
  print "Running: %s" % options.get('message', "None given")



run(utils.options())