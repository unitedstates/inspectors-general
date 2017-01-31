#!/usr/bin/env python

import datetime
import logging
from urllib.parse import urljoin

from utils import utils, inspector, admin

# https://oig.eeoc.gov/
archive = 1995

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#   - include all reports from old site (https://www.eeoc.gov/eeoc/oig/)
#   - some old reports could be run through an OCR maybe
#   - include full publication dates in HTML

AUDIT_REPORTS_URL = "https://oig.eeoc.gov/reports/audits"
CONGRESSIONAL_REPORTS_URL = "https://oig.eeoc.gov/reports/semi-annual"
REPORT_URLS = [
  ("audit", AUDIT_REPORTS_URL),
  ("congress", CONGRESSIONAL_REPORTS_URL),
]
INSPECTOR_URL = "https://oig.eeoc.gov/"

REPORT_PUBLISHED_MAP = {
  "1995-005-atr": datetime.datetime(1995, 7, 1),
  "1997-005-ape": datetime.datetime(1998, 6, 1),
  "1999-008-impr": datetime.datetime(1999, 10, 1),
  "1999-019-impr": datetime.datetime(1999, 10, 1),
  "2001-019-aic": datetime.datetime(2002, 9, 1),
  "2002-013-fin": datetime.datetime(2003, 12, 22),
  "2003-001-amr": datetime.datetime(2004, 9, 1),
  "2003-004-amr": datetime.datetime(2004, 1, 1),
  "2003-004-fin": datetime.datetime(2004, 11, 1),
  "2003-005-mis": datetime.datetime(2005, 9, 30),
  "2003-015-amr": datetime.datetime(2002, 10, 1),
  "2005-002-amr": datetime.datetime(2006, 7, 1),
  "2005-003-prop": datetime.datetime(2005, 5, 1),
  "2005-008-mgt": datetime.datetime(2005, 10, 1),
  "2006-002-fin": datetime.datetime(2006, 10, 1),
  "2006-007-amr": datetime.datetime(2007, 2, 1),
  "2007-003-amr": datetime.datetime(2007, 4, 1),
  "2007-007-adv": datetime.datetime(2009, 4, 24),
  "2007-011-rfpe": datetime.datetime(2008, 1, 1),
  "2007-012-amr": datetime.datetime(2008, 3, 27),
  "2008-003-amr": datetime.datetime(2008, 9, 26),
  "2008-006-fin": datetime.datetime(2008, 10, 1),
  "2008-012-aep": datetime.datetime(2008, 9, 30),
  "2009-004-fin": datetime.datetime(2009, 11, 13),
  "2010-009-aep": datetime.datetime(2011, 3, 10),
  "2011-001-aep": datetime.datetime(2011, 7, 15),
  "2011-002-aep": datetime.datetime(2011, 9, 30),
  "2011-002-fin": datetime.datetime(2011, 11, 11),
  "2011-005-fism": datetime.datetime(2011, 11, 21),
  "2011-apr-sep": datetime.datetime(2011, 11, 1),
  "2011-oct-mar": datetime.datetime(2011, 4, 30),
  "2012-001-fin": datetime.datetime(2012, 11, 15),
  "2012-003-fism": datetime.datetime(2012, 9, 1),
  "2012-008-purc": datetime.datetime(2013, 3, 26),
  "2012-009-rev": datetime.datetime(2013, 4, 9),
  "2012-010-pmev": datetime.datetime(2013, 3, 19),
  "2012-apr-sep": datetime.datetime(2012, 11, 1),
  "2012-oct-mar": datetime.datetime(2012, 4, 30),
  "2013-001-fin": datetime.datetime(2013, 12, 12),
  "2013-003-caro": datetime.datetime(2014, 9, 23),
  "2013-005-fism": datetime.datetime(2013, 12, 5),
  "2013-008-psa": datetime.datetime(2014, 9, 15),
  "2013-apr-sep": datetime.datetime(2013, 11, 6),
  "2013-oct-mar": datetime.datetime(2013, 4, 30),
  "2014-001-fin": datetime.datetime(2014, 11, 17),
  "2014-003-oe": datetime.datetime(2015, 5, 1),
  "2014-008-eoig": datetime.datetime(2014, 12, 16),
  "2014-apr-sep": datetime.datetime(2014, 10, 31),
  "2014-oct-mar-0": datetime.datetime(2014, 4, 30),
  "2015-001-fin": datetime.datetime(2015, 12, 16),
  "2015-001-iper": datetime.datetime(2015, 5, 13),
  "2015-001-lit": datetime.datetime(2016, 6, 1),
  "2015-003-eoig": datetime.datetime(2015, 12, 9),
  "2015-apr-sep": datetime.datetime(2015, 11, 1),
  "2015-oct-mar": datetime.datetime(2015, 4, 30),
  "2016-0004-aoig": datetime.datetime(2016, 5, 11),
  "2016-001-aoig": datetime.datetime(2016, 11, 15),
  "2016-008-eoig": datetime.datetime(2017, 1, 4),
  "2016-012-aep": datetime.datetime(2016, 9, 30),
  "2016-apr-sep": datetime.datetime(2016, 11, 1),
  "2016-oct-mar": datetime.datetime(2016, 5, 1),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, report_url in REPORT_URLS:
      doc = utils.beautifulsoup_from_url(report_url)
      results = doc.select("tbody tr > td:nth-of-type(1) a") or doc.select(".views-more-link")
      for result in results:
        report = report_from(result, year_range, report_type)
        if report:
          inspector.save_report(report)

def report_from(result, year_range, report_type):
  path = result.get("href")
  html_report_url = urljoin(INSPECTOR_URL, path)
  html_report = utils.beautifulsoup_from_url(html_report_url)
  report_id = path.split('/')[-1]
  title = html_report.find("span", {"property": "dc:title"})['content']
  fiscal_year = fiscal_year_parse(html_report)

  links = html_report.select(".file a")
  hrefs = filter_links(links)
  if len(hrefs) > 1:
    raise Exception("Found multiple links on {}:\n{}".format(html_report_url,
                                                             hrefs))
  if len(hrefs) == 0:
    raise Exception("Found no links on {}".format(html_report_url))
  pdf_report_url = hrefs[0]

  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  else:
    admin.log_no_date("eeoc", report_id, title, pdf_report_url)

  if fiscal_year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % pdf_report_url)
    return

  report = {
    'inspector': "eeoc",
    'inspector_url': INSPECTOR_URL,
    'agency': "eeoc",
    'agency_name': "Equal Employment Opportunity Commission",
    'report_id': report_id,
    'url': pdf_report_url,
    'title': title,
    'type': report_type,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }

  return report

def fiscal_year_parse(html_report):
  fiscal_year_text = (html_report
                      .find(class_="field-name-field-fiscal-year")
                      .find(class_="field-item")
                      .get_text())
  return int(fiscal_year_text)

def filter_links(links):
  return [link["href"] for link in links
          if ("Trans_Rept" not in link.text and
              "Transmittal" not in link.text)]

utils.run(run) if (__name__ == "__main__") else None
