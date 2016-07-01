#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector, admin

# http://arts.gov/oig
archive = 2005

# options:
#   standard since/year options for a year range to fetch from.
#   report_id: only bother to process a single report
#
# Notes for IG's web team:
# - Fix MISSING_IDS

AUDIT_REPORTS_URL = "http://arts.gov/oig/reports/audits"
SPECIAL_REVIEWS_URL = "http://arts.gov/oig/reports/specials"
SEMIANNUAL_REPORTS_URL = "http://arts.gov/oig/reports/semi-annual"
PEER_REVIEWS_URL = "http://arts.gov/oig/reports/external-peer-reviews"
FISMA_REPORTS_URL = "http://arts.gov/inspector-general/reports/internal-reviews"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "evaluation": SPECIAL_REVIEWS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
  "peer_review": PEER_REVIEWS_URL,
  "fisma": FISMA_REPORTS_URL,
}

MISSING_IDS = [
  "EA-perimeter-security-test-reload",
]

REPORT_PUBLISHED_MAP = {
  "2013-Peer-Review": datetime.datetime(2013, 12, 13),
  "2010-Peer-Review": datetime.datetime(2010, 8, 30),
  "2007-Peer-Review": datetime.datetime(2007, 3, 28),
  "mississippi-limited-audit-revised": datetime.datetime(2015, 11, 3),
  "maaf-final-report": datetime.datetime(2015, 5, 6),
  "louisiana-final-audit": datetime.datetime(2014, 12, 22),
  "DCCAH-Final-Report": datetime.datetime(2013, 9, 23),
  "MN-State-Arts-Board-LSA": datetime.datetime(2013, 3, 15),
  "MTG-LS-redacted": datetime.datetime(2013, 3, 1),
  "AMW-LSA-Final-Report": datetime.datetime(2013, 1, 11),
  "APAP-LSA-Report-080312": datetime.datetime(2012, 8, 3),
  "Illinois-Arts-Council-Report": datetime.datetime(2012, 4, 4),
  "American-Samoa": datetime.datetime(2011, 7, 15),
  "MSAC_Report_1": datetime.datetime(2011, 7, 25),
  "Family-Resources-Evaluation-Report": datetime.datetime(2009, 10, 30),
  "Virginia-Commission": datetime.datetime(2009, 8, 12),
  "Wisconsin-Arts-Board-Final-Report": datetime.datetime(2009, 6, 15),
  "PCA-Final-Report_0": datetime.datetime(2009, 4, 3),
  "hrac-final-debarment-report-5-13-2015": datetime.datetime(2015, 5, 13),
  "northwest-heritage-resources-final-report": datetime.datetime(2014, 11, 19),
  "2015-confluences-final-report": datetime.datetime(2014, 10, 20),
  "State-Education-Agency-DIrectors-SCE-07-14": datetime.datetime(2014, 7, 16),
  "Academy-of-American-Poets-SCE-7-14": datetime.datetime(2014, 7, 10),
  "Lincoln-Center-Final-SCE": datetime.datetime(2014, 5, 28),
  "American-Documentary-SCE-14-02": datetime.datetime(2014, 5, 19),
  "BRIC-Arts-SCE-3-25-14": datetime.datetime(2014, 3, 25),
  "Philadelphia-Orchestra-Association": datetime.datetime(2013, 3, 27),
  "Greater-Philadelphia-Alliance": datetime.datetime(2013, 2, 7),
  "FA-Report-NFT-Redacted": datetime.datetime(2013, 8, 28),
  "mtg-report-disposition-closeout-11-14": datetime.datetime(2013, 6, 5),
  "AFTA": datetime.datetime(2012, 9, 4),
  "SAH": datetime.datetime(2012, 7, 9),
  "APAP-Evaluation": datetime.datetime(2012, 6, 20),
  "DCASE": datetime.datetime(2012, 5, 1),
  "NBM": datetime.datetime(2011, 10, 24),
  "BSO": datetime.datetime(2011, 9, 7),
  "DSOHSCE": datetime.datetime(2010, 8, 5),
  "Mosaic": datetime.datetime(2010, 4, 30),
  "UMS": datetime.datetime(2010, 1, 28),
  "gulf-coast-youth-choirs": datetime.datetime(2009, 9, 30),
  "michigan-opera-theater": datetime.datetime(2009, 9, 30),
  "Florida-Orchestra-Report": datetime.datetime(2009, 9, 28),
  "artsandculturalaffairsweb": datetime.datetime(2009, 9, 23),
  "Sphinx-Organization": datetime.datetime(2009, 9, 23),
  "VirginIslandEvaluationReport": datetime.datetime(2009, 3, 25),
  "WoodlandPatternEvaluationReport": datetime.datetime(2008, 10, 8),
  "VSAEvaluationReport": datetime.datetime(2008, 10, 7),
  "TricklockEvaluationReport": datetime.datetime(2008, 10, 6),
  "LosReyesEvaluationReport": datetime.datetime(2008, 10, 2),
  "MusicTheatreGroup-Redacted-2008": datetime.datetime(2007, 11, 21),
  "LS-16-02-NASAA-Final-Report": datetime.datetime(2016, 2, 29),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  only_report_id = options.get('report_id')

  # Pull the reports
  for report_type, url in sorted(REPORT_URLS.items()):
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("div.field-item li")
    if not results:
      results = doc.select("div.field-item tr")
    if not results:
      raise inspector.NoReportsFoundError("National Endowment for the Arts (%s)" % report_type)
    for result in results:
      report = report_from(result, url, report_type, year_range)

      if report:
        # debugging convenience: can limit to single report
        if only_report_id and (report['report_id'] != only_report_id):
          continue

        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  link = result.find("a")
  if not link:
    return

  title = link.text
  report_url = urljoin(landing_url, link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)

  published_on = None
  try:
    published_on_text = result.select("td")[1].text.strip()
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%y')
  except (ValueError, IndexError):
    pass

  try:
    published_on_text = result.select("td")[1].text.strip()
    published_on = datetime.datetime.strptime(published_on_text, '%m/%d/%Y')
  except (ValueError, IndexError):
    pass

  if not published_on:
    try:
      published_on_text = title.split("-")[-1].split("–")[-1].strip()
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except ValueError:
      pass

  if not published_on:
    if report_id in REPORT_PUBLISHED_MAP:
      published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    admin.log_no_date("nea", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'nea',
    'inspector_url': 'http://arts.gov/oig',
    'agency': 'nea',
    'agency_name': 'National Endowment for the Arts',
    'type': report_type,
    'landing_url': landing_url,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if report_id in MISSING_IDS:
    report['unreleased'] = True
    report['missing'] = True
    report['url'] = None
  return report

utils.run(run) if (__name__ == "__main__") else None
