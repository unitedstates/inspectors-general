#!/usr/bin/env python

import datetime
import logging
import re
from urllib.parse import urljoin

from utils import utils, inspector, admin

# http://www.gpo.gov/oig/
archive = 2004

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "http://www.gpo.gov/oig/audits.htm"
SEMIANNUAL_REPORTS_URL = "http://www.gpo.gov/oig/semi-anual.htm"

HEADER_TITLES = [
  'Report #',
  'Date',
]

UNPUBLISHED_REPORT_TITLES = (
  "Unscheduled and Unpaid Absenteeism in the Office of Plant Operations",
  "GPO Purchase Card Program Management Controls",
  "Passport Security (FORTUNA System)",
  "Blank Passport Product Integrity & Security",
  "Smart Card/PKI Business Case",
  "Review of GPO's Internal Control Program",
  "PKI Compliance Audit",
)

REPORT_URLS = {
  "audit": AUDIT_REPORTS_URL,
  "semiannual_report": SEMIANNUAL_REPORTS_URL,
}

REPORT_PUBLISHED_MAP = {
  "17-01": datetime.datetime(2016, 12, 6),
  "17-03": datetime.datetime(2016, 12, 16),
  "17-04": datetime.datetime(2017, 1, 19),
  "17-05": datetime.datetime(2017, 1, 19),
  "17-06": datetime.datetime(2017, 3, 1),
  "17-07": datetime.datetime(2017, 3, 17),
  "17-08": datetime.datetime(2017, 3, 28),
  "17-09": datetime.datetime(2017, 4, 1),
  "17-10": datetime.datetime(2017, 7, 1),
  "17-11": datetime.datetime(2017, 7, 1),
  "17-12": datetime.datetime(2017, 7, 1),
  "17-13": datetime.datetime(2017, 8, 1),
  "17-14": datetime.datetime(2017, 8, 1),
  "17-15": datetime.datetime(2017, 8, 1),
  "17-16": datetime.datetime(2017, 8, 1),
  "16-01": datetime.datetime(2015, 10, 26),
  "16-02": datetime.datetime(2015, 10, 21),
  "16-03": datetime.datetime(2015, 12, 23),
  "16-04": datetime.datetime(2016, 1, 22),
  "16-05": datetime.datetime(2016, 1, 22),
  "16-06": datetime.datetime(2016, 2, 25),
  "16-07": datetime.datetime(2016, 1, 1),
  "16-08": datetime.datetime(2016, 1, 1),
  "16-09": datetime.datetime(2016, 1, 1),
  "16-10": datetime.datetime(2016, 3, 30),
  "16-11": datetime.datetime(2016, 1, 1),
  "16-12": datetime.datetime(2016, 1, 1),
  "16-13": datetime.datetime(2016, 1, 1),
  "16-14": datetime.datetime(2016, 5, 10),
  "16-15": datetime.datetime(2016, 5, 12),
  "16-16": datetime.datetime(2016, 6, 1),
  "16-17": datetime.datetime(2016, 6, 1),
  "16-18": datetime.datetime(2016, 6, 1),
  "16-19": datetime.datetime(2016, 9, 29),
  "16-20": datetime.datetime(2016, 9, 1),
  "16-21": datetime.datetime(2016, 9, 29),
  "16-22": datetime.datetime(2016, 9, 30),
  "16-23": datetime.datetime(2016, 9, 23),
  "16-24": datetime.datetime(2016, 9, 23),
  "15-01": datetime.datetime(2015, 1, 1),
  "15-02": datetime.datetime(2015, 3, 20),
  "15-03": datetime.datetime(2015, 2, 5),
  "15-04": datetime.datetime(2015, 2, 13),
  "15-05": datetime.datetime(2015, 1, 1),
  "15-06": datetime.datetime(2015, 3, 20),
  "15-07": datetime.datetime(2015, 3, 24),
  "15-08": datetime.datetime(2015, 1, 1),
  "15-09": datetime.datetime(2015, 3, 27),
  "15-10": datetime.datetime(2015, 3, 26),
  "15-11": datetime.datetime(2015, 3, 31),
  "15-12": datetime.datetime(2015, 1, 1),
  "15-13": datetime.datetime(2015, 1, 1),
  "15-14": datetime.datetime(2015, 1, 1),
  "15-15": datetime.datetime(2015, 1, 1),
  "15-16": datetime.datetime(2015, 1, 1),
  "15-17": datetime.datetime(2015, 1, 1),
  "15-18": datetime.datetime(2015, 9, 3),
  "15-19": datetime.datetime(2015, 9, 25),
  "15-20": datetime.datetime(2015, 9, 24),
  "15-21": datetime.datetime(2015, 9, 24),
  "14-01": datetime.datetime(2013, 11, 13),
  "14-02": datetime.datetime(2013, 11, 29),
  "14-03": datetime.datetime(2013, 12, 5),
  "14-04": datetime.datetime(2014, 1, 1),
  "14-05": datetime.datetime(2014, 1, 1),
  "14-06": datetime.datetime(2014, 1, 1),
  "14-07": datetime.datetime(2014, 3, 24),
  "14-08": datetime.datetime(2014, 3, 25),
  "14-09": datetime.datetime(2014, 2, 14),
  "14-10": datetime.datetime(2014, 3, 27),
  "14-11": datetime.datetime(2014, 3, 14),
  "14-12": datetime.datetime(2014, 4, 22),
  "14-13": datetime.datetime(2014, 1, 1),
  "14-14": datetime.datetime(2014, 8, 1),
  "14-15": datetime.datetime(2014, 7, 11),
  "14-16": datetime.datetime(2014, 9, 26),
  "14-17": datetime.datetime(2014, 5, 2),
  "14-18": datetime.datetime(2014, 1, 1),
  "14-19": datetime.datetime(2014, 9, 12),
  "14-20": datetime.datetime(2014, 9, 12),
  "14-21": datetime.datetime(2014, 9, 23),
  "13-01": datetime.datetime(2013, 1, 15),
  "13-02": datetime.datetime(2013, 3, 27),
  "13-03": datetime.datetime(2013, 1, 1),
  "13-04": datetime.datetime(2012, 12, 27),
  "13-05": datetime.datetime(2013, 2, 13),
  "13-06": datetime.datetime(2013, 3, 29),
  "13-07": datetime.datetime(2013, 1, 1),
  "13-08": datetime.datetime(2013, 1, 1),
  "13-09": datetime.datetime(2013, 2, 28),
  "13-10": datetime.datetime(2013, 3, 20),
  "13-11": datetime.datetime(2013, 1, 1),
  "13-12": datetime.datetime(2013, 3, 29),
  "13-13": datetime.datetime(2013, 9, 23),
  "13-14": datetime.datetime(2013, 8, 7),
  "13-15": datetime.datetime(2013, 6, 28),
  "13-17": datetime.datetime(2013, 1, 1),
  "13-18": datetime.datetime(2013, 9, 6),
  "13-19": datetime.datetime(2013, 9, 6),
  "12-02": datetime.datetime(2011, 12, 16),
  "12-02a": datetime.datetime(2011, 12, 21),
  "12-03": datetime.datetime(2012, 1, 18),
  "12-04": datetime.datetime(2012, 2, 24),
  "12-05": datetime.datetime(2012, 1, 27),
  "12-06": datetime.datetime(2012, 2, 24),
  "12-07": datetime.datetime(2012, 2, 14),
  "12-08": datetime.datetime(2012, 3, 30),
  "12-09": datetime.datetime(2012, 1, 1),
  "12-10": datetime.datetime(2012, 1, 1),
  "12-11": datetime.datetime(2012, 1, 1),
  "12-12": datetime.datetime(2012, 4, 27),
  "12-13": datetime.datetime(2012, 1, 1),
  "12-14": datetime.datetime(2012, 7, 25),
  "12-15": datetime.datetime(2012, 7, 13),
  "12-16": datetime.datetime(2012, 9, 21),
  "12-17": datetime.datetime(2012, 9, 18),
  "12-18": datetime.datetime(2012, 9, 28),
  "12-19": datetime.datetime(2012, 9, 28),
  "12-20": datetime.datetime(2012, 9, 1),
  "12-22": datetime.datetime(2012, 9, 18),
  "12-23": datetime.datetime(2012, 9, 18),
  "12-24": datetime.datetime(2012, 9, 21),
  "11-01": datetime.datetime(2010, 12, 16),
  "11-02": datetime.datetime(2010, 12, 6),
  "11-03": datetime.datetime(2010, 12, 15),
  "11-04": datetime.datetime(2010, 12, 21),
  "11-06": datetime.datetime(2011, 3, 31),
  "Unnumbered": datetime.datetime(2011, 3, 25),
  "10-01": datetime.datetime(2009, 12, 2),
  "10-02": datetime.datetime(2010, 1, 8),
  "10-05": datetime.datetime(2010, 3, 24),
  "10-06": datetime.datetime(2010, 3, 31),
  "10-07": datetime.datetime(2010, 6, 18),
  "10-08": datetime.datetime(2010, 9, 16),
  "10-09": datetime.datetime(2010, 9, 20),
  "09-01": datetime.datetime(2008, 11, 4),
  "09-02": datetime.datetime(2008, 12, 22),
  "09-03": datetime.datetime(2008, 12, 24),
  "09-04": datetime.datetime(2008, 12, 24),
  "09-05": datetime.datetime(2008, 12, 24),
  "09-06": datetime.datetime(2009, 1, 15),
  "09-07": datetime.datetime(2009, 3, 20),
  "09-08": datetime.datetime(2009, 3, 31),
  "09-10": datetime.datetime(2009, 9, 23),
  "09-11": datetime.datetime(2009, 9, 23),
  "09-12": datetime.datetime(2009, 9, 30),
  "09-13": datetime.datetime(2009, 9, 30),
  "09-14": datetime.datetime(2009, 9, 30),
  "08-01": datetime.datetime(2007, 11, 1),
  "08-02": datetime.datetime(2007, 11, 19),
  "08-03": datetime.datetime(2008, 1, 28),
  "08-04": datetime.datetime(2008, 3, 28),
  "08-05": datetime.datetime(2008, 1, 1),
  "08-06": datetime.datetime(2008, 3, 31),
  "08-07": datetime.datetime(2008, 5, 30),
  "08-08": datetime.datetime(2008, 8, 8),
  "08-09": datetime.datetime(2008, 8, 8),
  "08-10": datetime.datetime(2008, 9, 11),
  "08-11": datetime.datetime(2008, 9, 18),
  "08-12": datetime.datetime(2008, 9, 30),
  "08-13": datetime.datetime(2008, 9, 30),
  "07-01": datetime.datetime(2006, 11, 20),
  "07-02": datetime.datetime(2006, 11, 27),
  "07-03": datetime.datetime(2006, 11, 29),
  "07-04": datetime.datetime(2007, 3, 30),
  "07-05": datetime.datetime(2007, 3, 31),
  "07-06": datetime.datetime(2007, 5, 9),
  "07-07": datetime.datetime(2007, 9, 17),
  "07-08": datetime.datetime(2007, 9, 19),
  "07-09": datetime.datetime(2007, 9, 27),
  "07-10": datetime.datetime(2007, 9, 28),
  "06-01": datetime.datetime(2006, 1, 1),
  "06-02": datetime.datetime(2006, 3, 28),
  "06-03": datetime.datetime(2006, 3, 31),
  "06-04": datetime.datetime(2006, 3, 31),
  "06-05": datetime.datetime(2006, 5, 16),
  "06-06": datetime.datetime(2006, 9, 22),
  "06-07": datetime.datetime(2006, 8, 11),
  "06-08": datetime.datetime(2006, 9, 29),
  "05-01": datetime.datetime(2004, 12, 20),
  "05-02": datetime.datetime(2005, 3, 31),
  "05-03": datetime.datetime(2005, 3, 31),
  "05-04": datetime.datetime(2005, 9, 30),
  "AI0501": datetime.datetime(2005, 9, 30),
  "AI0502": datetime.datetime(2005, 1, 1),
  "AI0503": datetime.datetime(2005, 1, 1),
  "AI0504": datetime.datetime(2005, 1, 1),
  "AI0505": datetime.datetime(2005, 1, 1),
  "AI0506": datetime.datetime(2005, 1, 1),
  "AI0401": datetime.datetime(2004, 2, 12),
  "AI0402": datetime.datetime(2004, 3, 31),
  "AI0403": datetime.datetime(2005, 1, 1),
  "AI0404": datetime.datetime(2005, 1, 1),
  "04-08-243": datetime.datetime(2004, 9, 30),
  "04-01-335": datetime.datetime(2004, 3, 31),
}

REPORT_ID_RE = re.compile("(?:[0-9]{2}-[0-9]{2}|AI[0-9]{4})")
DATE_RE = re.compile("[^0-9]([01][0-9]-[0123][0-9]-[0-9][0-9])[^0-9]")


def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, url in REPORT_URLS.items():
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("div.section1 div.ltext > table tr")
    if not results:
      results = doc.select("td.three-col-layout-middle div.ltext > table tr")
    if not results:
      raise inspector.NoReportsFoundError("Government Publishing Office (%s)" % url)
    for result in results:
      if (not result.text.strip() or
              result.find("th") or
              result.find("strong") or
              result.contents[1].text in HEADER_TITLES):
        # Skip header rows
        continue
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)


def report_from(result, landing_url, report_type, year_range):
  title = result.select("td")[-1].text
  title = re.sub("\\s+", " ", title)

  report_id_match = REPORT_ID_RE.match(result.td.text.strip())
  if ("contains sensitive information" in title or
          "This correspondence will not be posted" in title or
          title in UNPUBLISHED_REPORT_TITLES):
    unreleased = True
    report_url = None
    if report_id_match:
      report_id = report_id_match.group(0)
    else:
      report_id = inspector.slugify("-".join(title.strip().split())[:100])
  else:
    unreleased = False
    link = result.find("a")
    report_id = inspector.slugify(link.text.strip())
    if link.get('href') == "#":
      unreleased = True
      report_url = None
    else:
      report_url = urljoin(landing_url, link.get('href'))
      if landing_url == SEMIANNUAL_REPORTS_URL:
        if title.find("Transmittal Letter") != -1:
          report_id = report_id + "-transmittal"

  published_on = None
  try:
    published_on = datetime.datetime.strptime(link.text.strip(), '%m.%d.%y')
  except (ValueError, UnboundLocalError):
    pass

  if not published_on:
    if report_url:
      date_match = DATE_RE.search(report_url)
      if date_match:
        date_text = date_match.group(1)
        published_on = datetime.datetime.strptime(date_text, "%m-%d-%y")

  if not published_on:
    if report_id in REPORT_PUBLISHED_MAP:
      published_on = REPORT_PUBLISHED_MAP[report_id]

  if not published_on:
    admin.log_no_date("gpo", report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'gpo',
    'inspector_url': 'http://www.gpo.gov/oig/',
    'agency': 'gpo',
    'agency_name': 'Government Publishing Office',
    'file_type': 'pdf',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
