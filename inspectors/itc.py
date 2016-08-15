#!/usr/bin/env python

import datetime
import logging
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://www.usitc.gov/oig.htm
archive = 1990

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# - None of the audit reports have dates in the visible metadata!
# - There are some typos in report numbers and link URLS for audit reports
#   between 1999 and 2001. See the comments in report_from() for details.

AUDIT_REPORTS_URL = "https://www.usitc.gov/oig/audit_reports.html"
SEMIANNUAL_REPORTS_URL = "https://www.usitc.gov/oig/semiannual_reports.htm"
PEER_REVIEWS_URL = "https://www.usitc.gov/oig/peer_reviews.htm"

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  # "semiannual_report": SEMIANNUAL_REPORTS_URL,
  # "peer_review": PEER_REVIEWS_URL,
}

REPORT_PUBLISHED_MAP = {
  "OIG-MR-16-14": datetime.datetime(2016, 8, 12),
  "OIG-ER-16-13": datetime.datetime(2016, 7, 25),
  "OIG-MR-16-12": datetime.datetime(2016, 5, 10),
  "OIG-ML-16-11": datetime.datetime(2016, 5, 12),
  "OIG-MR-16-10": datetime.datetime(2016, 2, 10),
  "OIG-MR-16-09": datetime.datetime(2016, 1, 29),
  "OIG-Report": datetime.datetime(2016, 1, 29),
  "OIG-ML-16-08": datetime.datetime(2015, 12, 17),
  "OIG-ML-16-07": datetime.datetime(2015, 11, 23),
  "OIG-MR-16-06": datetime.datetime(2015, 11, 13),
  "OIG-AR-16-05": datetime.datetime(2015, 11, 9),
  "OIG-AR-16-04": datetime.datetime(2015, 11, 9),
  "OIG-AR-16-03": datetime.datetime(2015, 11, 9),
  "OIG-ER-16-02": datetime.datetime(2015, 10, 14),
  "OIG-ER-16-01": datetime.datetime(2015, 10, 8),
  "OIG-MR-15-16": datetime.datetime(2015, 9, 30),
  "OIG-ML-15-15": datetime.datetime(2015, 9, 8),
  "OIG-AR-15-14": datetime.datetime(2015, 9, 2),
  "OIG-MR-15-13": datetime.datetime(2015, 8, 14),
  "OIG-AR-15-12": datetime.datetime(2015, 8, 11),
  "OIG-AR-15-11": datetime.datetime(2015, 7, 22),
  "OIG-MR-15-10": datetime.datetime(2015, 5, 13),
  "OIG-MR-15-09": datetime.datetime(2015, 1, 30),
  "OIG-MR-15-08": datetime.datetime(2015, 1, 30),
  "OIG-ML-15-07": datetime.datetime(2015, 1, 8),
  "OIG-ML-15-06": datetime.datetime(2014, 12, 1),
  "OIG-AR-15-05": datetime.datetime(2014, 11, 12),
  "OIG-AR-15-04": datetime.datetime(2014, 11, 12),
  "OIG-AR-15-03": datetime.datetime(2014, 11, 12),
  "OIG-ER-15-02": datetime.datetime(2014, 10, 7),
  "OIG-MR-15-01": datetime.datetime(2014, 10, 6),
  "OIG-AR-14-13": datetime.datetime(2014, 7, 7),
  "OIG-ML-14-12": datetime.datetime(2014, 6, 9),
  "OIG-ML-14-11": datetime.datetime(2014, 3, 31),
  "OIG-MR-14-10": datetime.datetime(2014, 1, 31),
  "OIG-MR-14-09": datetime.datetime(2013, 12, 2),
  "OIG-ML-14-08": datetime.datetime(2013, 12, 24),
  "OIG-AR-14-07": datetime.datetime(2013, 12, 13),
  "OIG-AR-14-06": datetime.datetime(2013, 12, 13),
  "OIG-AR-14-05": datetime.datetime(2013, 12, 13),
  "OIG-ML-14-04": datetime.datetime(2013, 12, 5),
  "OIG-MR-14-03": datetime.datetime(2013, 11, 15),
  "OIG-AR-14-02": datetime.datetime(2013, 11, 12),
  "OIG-ML-14-01": datetime.datetime(2013, 11, 7),
  "OIG-AR-13-10": datetime.datetime(2013, 6, 24),
  "OIG-AR-13-09": datetime.datetime(2013, 6, 24),
  "OIG-ER-13-08": datetime.datetime(2013, 3, 20),
  "OIG-MR-13-07": datetime.datetime(2012, 11, 14),
  "OIG-ML-13-06": datetime.datetime(2012, 12, 19),
  "OIG-AR-13-05": datetime.datetime(2012, 11, 9),
  "OIG-AR-13-04": datetime.datetime(2012, 11, 9),
  "OIG-AR-13-03": datetime.datetime(2012, 11, 9),
  "OIG-MR-13-02": datetime.datetime(2012, 10, 15),
  "OIG-AR-13-01": datetime.datetime(2012, 10, 19),
  "OIG-MR-12-12": datetime.datetime(2011, 11, 10),
  "OIG-ER-12-11": datetime.datetime(2012, 9, 12),
  "OIG-AR-12-10": datetime.datetime(2012, 8, 16),
  "OIG-ER-12-09": datetime.datetime(2012, 6, 20),
  "OIG-ER-12-08": datetime.datetime(2012, 6, 13),
  "OIG-ER-12-07": datetime.datetime(2012, 1, 25),
  "OIG-AR-12-06": datetime.datetime(2012, 1, 23),
  "OIG-ML-12-05": datetime.datetime(2011, 12, 12),
  "OIG-AR-12-04": datetime.datetime(2011, 11, 10),
  "OIG-AR-12-03": datetime.datetime(2011, 11, 10),
  "OIG-AR-12-02": datetime.datetime(2011, 11, 10),
  "OIG-MR-12-01": datetime.datetime(2011, 10, 15),
  "OIG-AR-11-17": datetime.datetime(2011, 9, 30),
  "OIG-AR-11-16": datetime.datetime(2011, 9, 29),
  "OIG-AR-11-15": datetime.datetime(2011, 9, 28),
  "OIG-SP-11-14": datetime.datetime(2011, 9, 14),
  "OIG-SP-11-13": datetime.datetime(2011, 9, 12),
  "OIG-SP-11-12": datetime.datetime(2011, 9, 9),
  "OIG-AR-11-11": datetime.datetime(2011, 6, 29),
  "OIG-AR-11-10": datetime.datetime(2011, 4, 28),
  "OIG-AR-11-09": datetime.datetime(2010, 10, 15),
  "OIG-AR-11-08": datetime.datetime(2011, 3, 14),
  "OIG-AR-11-07": datetime.datetime(2010, 12, 29),
  "OIG-ML-11-06": datetime.datetime(2010, 12, 1),
  "OIG-MR-11-05": datetime.datetime(2010, 11, 15),
  "OIG-AR-11-04": datetime.datetime(2010, 11, 10),
  "OIG-AR-11-03": datetime.datetime(2010, 11, 10),
  "OIG-AR-11-02": datetime.datetime(2010, 11, 10),
  "OIG-AR-11-01": datetime.datetime(2010, 10, 19),
  "OIG-AR-10-10": datetime.datetime(2010, 7, 13),
  "OIG-AR-09-10": datetime.datetime(2010, 6, 23),
  "OIG-AR-08-10": datetime.datetime(2010, 7, 7),
  "OIG-AR-07-10": datetime.datetime(2010, 7, 1),
  "OIG-MR-06-10": datetime.datetime(2009, 11, 18),
  "OIG-AR-05-10": datetime.datetime(2010, 3, 9),
  "OIG-ML-04-10": datetime.datetime(2009, 12, 8),
  "CO80-HH-004": datetime.datetime(2010, 3, 3),
  "IG-HH-001": datetime.datetime(2010, 3, 9),
  "OIG-AR-03-10": datetime.datetime(2009, 11, 6),
  "OIG-AR-02-10": datetime.datetime(2009, 11, 6),
  "OIG-AR-01-10": datetime.datetime(2009, 11, 6),
  "Audit-Report-OIG-AR-01-09": datetime.datetime(2009, 3, 25),
  "Audit-Report-OIG-AR-01-08": datetime.datetime(2009, 1, 29),
  "OIG-AR-04-07": datetime.datetime(2007, 10, 1),
  "OIG-AR-03-07": datetime.datetime(2007, 6, 5),
  "Audit-Report-OIG-AR-02-07": datetime.datetime(2007, 5, 16),
  "Audit-Report-OIG-AR-01-07": datetime.datetime(2006, 11, 14),
  "OIG-AR-03-06": datetime.datetime(2006, 9, 29),
  "Audit-Report-OIG-AR-02-06": datetime.datetime(2006, 3, 31),
  "Audit-Report-OIG-AR-01-06": datetime.datetime(2005, 11, 14),
  "OIG-AR-04-05": datetime.datetime(2005, 9, 27),
  "Audit-Report-OIG-AR-02-05": datetime.datetime(2004, 11, 9),
  "Audit-Report-OIG-AR-03-05": datetime.datetime(2005, 3, 24),
  "Audit-Report-01-05": datetime.datetime(2004, 10, 6),
  "Audit-Report-01-04": datetime.datetime(2004, 5, 26),
  "Inspection-Report-01-04": datetime.datetime(2004, 9, 30),
  "Audit-Report-03-03": datetime.datetime(2003, 9, 22),
  "Audit-Report-02-03": datetime.datetime(2003, 7, 24),
  "Audit-Report-01-03": datetime.datetime(2003, 1, 28),
  "Inspection-Report-01-03": datetime.datetime(2003, 1, 1),
  "Audit-Report-03-02": datetime.datetime(2002, 9, 30),
  "Audit-Report-02-02": datetime.datetime(2002, 9, 13),
  "Inspection-Report-02-02": datetime.datetime(2002, 9, 25),
  "Audit-Report-01-02": datetime.datetime(2002, 3, 29),
  "Inspection-Report-01-02": datetime.datetime(2002, 9, 23),
  "Inspection-Report-06-01": datetime.datetime(2002, 3, 27),
  "Inspection-Report-02-01": datetime.datetime(2001, 2, 16),
  "Audit-Report-02-01": datetime.datetime(2001, 9, 10),
  "Inspection-Report-01-01": datetime.datetime(2001, 2, 14),
  "Audit-Report-01-01": datetime.datetime(2001, 3, 20),
  "Audit-Report-05-00": datetime.datetime(2001, 3, 7),
  "Audit-Report-04-00": datetime.datetime(2000, 7, 25),
  "Audit-Report-03-00": datetime.datetime(2000, 3, 24),
  "Inspection-Report-03-00": datetime.datetime(2000, 9, 29),
  "Audit-Report-02-00": datetime.datetime(2000, 2, 29),
  "Inspection-Report-02-00": datetime.datetime(1999, 12, 20),
  "Audit-Report-01-00": datetime.datetime(2000, 9, 29),
  "Inspection-Report-01-00": datetime.datetime(1999, 11, 23),
  "Inspection-Report-06-99": datetime.datetime(1999, 9, 3),
  "Inspection-Report-05-99": datetime.datetime(1999, 7, 23),
  "Inspection-Report-04-99": datetime.datetime(1999, 6, 28),
  "Audit-Report-04-99": datetime.datetime(1999, 3, 1),
  "Audit-Report-03-99": datetime.datetime(1999, 2, 1),
  "Inspection-Report-03-99": datetime.datetime(1999, 4, 1),
  "Audit-Report-02-99": datetime.datetime(1998, 12, 1),
  "Inspection-Report-02-99": datetime.datetime(1998, 12, 24),
  "Audit-Report-01-99": datetime.datetime(1998, 10, 1),
  "Inspection-Report-01-99": datetime.datetime(1998, 12, 24),
  "Audit-Report-03-98": datetime.datetime(1998, 6, 1),
  "Inspection-Report-03-98": datetime.datetime(1998, 6, 8),
  "Audit-Report-02-98": datetime.datetime(1998, 3, 1),
  "Inspection-Report-02-98": datetime.datetime(1998, 5, 1),
  "Inspection-Report-01-98": datetime.datetime(1998, 3, 6),
  "Audit-Report-01-98": datetime.datetime(1998, 2, 1),
  "Inspection-Report-05-97": datetime.datetime(1997, 9, 29),
  "Inspection-Report-04-97": datetime.datetime(1997, 9, 25),
  "Inspection-Report-03-97": datetime.datetime(1997, 3, 31),
  "Audit-Report-IG-02-97": datetime.datetime(1997, 3, 1),
  "Inspection-Report-02-97": datetime.datetime(1997, 3, 20),
  "Inspection-Report-01-97": datetime.datetime(1996, 12, 24),
  "Audit-Report-IG-01-97": datetime.datetime(1996, 10, 1),
  "Audit-Report-IG-03-96": datetime.datetime(1996, 8, 1),
  "Audit-Report-IG-02-96": datetime.datetime(1996, 4, 1),
  "Audit-Report-IG-01-96": datetime.datetime(1996, 3, 1),
  "Audit-Report-IG-01-95": datetime.datetime(1995, 7, 1),
  "Audit-Report-IG-05-94": datetime.datetime(1994, 9, 1),
  "Audit-Report-IG-04-94": datetime.datetime(1994, 8, 1),
  "Audit-Report-IG-03-94": datetime.datetime(1994, 8, 1),
  "Audit-Report-IG-02-94": datetime.datetime(1994, 4, 1),
  "Audit-Report-IG-01-94": datetime.datetime(1994, 2, 1),
  "Audit-Report-IG-04-93": datetime.datetime(1993, 9, 1),
  "Audit-Report-IG-03-93": datetime.datetime(1993, 9, 1),
  "Audit-Report-IG-02-93": datetime.datetime(1993, 6, 1),
  "Audit-Report-IG-01-93": datetime.datetime(1993, 3, 1),
  "Audit-Report-IG-04-92": datetime.datetime(1992, 9, 1),
  "Audit-Report-IG-03-92": datetime.datetime(1992, 8, 1),
  "Audit-Report-IG-02-92": datetime.datetime(1992, 8, 1),
  "Audit-Report-IG-01-92": datetime.datetime(1991, 11, 1),
  "IG-09-91": datetime.datetime(1991, 9, 1),
  "IG-08-91": datetime.datetime(1991, 9, 1),
  "IG-07-91": datetime.datetime(1991, 9, 1),
  "IG-06-91": datetime.datetime(1991, 7, 1),
  "IG-05-91": datetime.datetime(1991, 4, 1),
  "IG-04-91": datetime.datetime(1991, 3, 1),
  "IG-03-91": datetime.datetime(1991, 2, 1),
  "IG-02-91": datetime.datetime(1990, 11, 1),
  "IG-01-91": datetime.datetime(1991, 11, 1),
  "IG-07-90": datetime.datetime(1990, 9, 1),
  "IG-06-90": datetime.datetime(1990, 9, 1),
  "IG-05-90": datetime.datetime(1990, 7, 1),
  "IG-04-90": datetime.datetime(1990, 7, 1),
  "IG-03-90": datetime.datetime(1990, 2, 1),
  "IG-02-90": datetime.datetime(1990, 2, 1),
  "IG-01-90": datetime.datetime(1989, 10, 1),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the audit reports
  doc = utils.beautifulsoup_from_url(AUDIT_REPORTS_URL)

  headers = set([a.parent for a in
                 doc.find_all("a", id=re.compile("^[0-9]{4}$"))])
  headers.update(doc.find_all("p", class_="Ptitle1"))
  headers = sorted(headers, key=lambda p: int(p.text.strip()), reverse=True)
  if not headers:
    raise inspector.NoReportsFoundError("ITC")

  for header in headers:
    year = int(header.text.strip())
    results = header.findNextSibling("ul").select("li")

    for result in results:
      if not inspector.sanitize(result.text):
        logging.debug("Skipping empty list item.")
        continue

      report = audit_report_from(year, result, AUDIT_REPORTS_URL, year_range)
      if report:
        inspector.save_report(report)

global flag_inspection_report_01_01
flag_inspection_report_01_01 = False

def audit_report_from(year, result, landing_url, year_range):
  link = result.find("a", text=True)
  report_url = urljoin(landing_url, link.get('href'))
  report_id = "-".join(link.text.split()).replace(':', '')
  result_text = [x for x in result.stripped_strings]
  title = " ".join(result_text[0].split())
  unreleased = False

  # Some reports have the wrong link and/or number listed on the website
  if report_id == "Inspection-Report-03-99" and \
        title.find("Evaluation of the Commission's Passport System's " \
        "Security") != -1:
    # The title doesn't match the ID or URL, and this title doesn't show up
    # anywhere else, so patch in the correct ID/URL and save the report.
    report_id = "Inspection-Report-01-99"
    report_url = "https://www.usitc.gov/oig/documents/OIG-IR-01-99.pdf"
  elif report_id == "Inspection-Report-02-00" and \
        title.find("Second Follow-up Review of Commission's Preparation for " \
        "Year 2000") != -1:
    # The title doesn't match the ID or URL, but the ID/URL is listed with the
    # correct title elsewhere, and the title is listed with the correct ID/URL
    # elsewhere, so we can discard this result.
    return
  elif report_id == "Inspection-Report-01-01" and \
        title.find("Self-Assessment of the Commission's Human Capital") != -1:
    # There are two identical links for the same report, keep track and
    # discard the second one. Normally this would be achieved by discarding all
    # duplicate links, but given the other link/text mismatches, it would be
    # best to address this as a special case, in case there are similar typos
    # in the future.
    global flag_inspection_report_01_01
    if flag_inspection_report_01_01:
      return
    else:
      flag_inspection_report_01_01 = True
  elif report_id == "Inspection-Report-02-01" and \
        title.find("Assessment of the Commission's Family-Friendly Programs") != -1:
    # The report ID and URL for this assessment are wrong, so we will mark it
    # as unreleased.
    report_id = "family-friendly-programs"
    report_url = None
    unreleased = True
    landing_url = AUDIT_REPORTS_URL

  estimated_date = False
  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    try:
      published_on_text = title.split("(")[0].strip()
      published_on = datetime.datetime.strptime(published_on_text, '%B %Y')
    except ValueError:
      pass

  if landing_url == SEMIANNUAL_REPORTS_URL and link.text.find("-") == -1:
    # Need to add a date to some semiannual report IDs
    report_id = "%s-%s" % (report_id, published_on.strftime("%m-%y"))

  if not published_on:
    admin.log_no_date("itc", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'itc',
    'inspector_url': 'https://www.usitc.gov/oig.htm',
    'agency': 'itc',
    'agency_name': 'International Trade Commission',
    'type': 'audit',
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if estimated_date:
    report['estimated_date'] = estimated_date
  if unreleased:
    report['unreleased'] = True
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
