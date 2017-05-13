#!/usr/bin/env python

from utils import utils, inspector
from datetime import datetime
import urllib.parse
import logging
import re

archive = 2002

# options:
#   standard since/year options for a year range to fetch from.
#
#   component: limit to a specific component. See COMPONENTS dict at bottom.
#   limit: only download X number of reports (per component)
#   report_id: use in conjunction with 'component' to get only one report


def run(options):
  year_range = inspector.year_range(options, archive)

  component = options.get('component')
  if component:
    components = [component]
  else:
    components = sorted(COMPONENTS.keys())

  report_id = options.get('report_id')

  limit = int(options.get('limit', 0))

  all_audit_reports = {}

  for component in components:
    logging.info("## Fetching reports for component %s" % component)
    url = url_for(options, component)
    doc = utils.beautifulsoup_from_url(url)

    results = doc.select("#content-area tbody tr")
    if not results:
      raise inspector.NoReportsFoundError("DHS (%s)" % component)

    count = 0
    for result in results:
      report = report_from(result, component, url)
      if not report:
        continue

      if report_id and (report_id != report['report_id']):
        continue

      if inspector.year_from(report) not in year_range:
        # logging.info("[%s] Skipping, not in requested range." % report['report_id'])
        continue

      key = (report["report_id"], report["title"])
      if key in all_audit_reports:
        all_audit_reports[key]["agency"] = "{}, {}".format(all_audit_reports[key]["agency"],
                                                           report["agency"])
        all_audit_reports[key]["agency_name"] = "{}, {}".format(all_audit_reports[key]["agency_name"],
                                                                report["agency_name"])
      else:
        all_audit_reports[key] = report

      count += 1
      if limit and (count >= limit):
        break

    logging.info("## Fetched %i reports for component %s\n\n" % (count, component))

  for report in all_audit_reports.values():
    inspector.save_report(report)

PDF_DESCRIPTION_RE = re.compile("(.*)\\(PDF, [0-9]+ pages - [0-9.]+ ?[mMkK][bB]\\)")


def report_from(result, component, url):
  report = {
    'inspector': 'dhs',
    'inspector_url': 'https://www.oig.dhs.gov/'
  }

  link = result.select("td")[1].select("a")[0]
  href = link['href']
  href = href.replace("/index.php/", "/")
  report_url = urllib.parse.urljoin(url, href)
  title = link.text.strip()
  title = title.replace("\xa0", " ")
  title = title.replace("  ", " ")
  title = title.replace(", , ", ", ")
  title = title.rstrip("( ,.")
  pdf_desc_match = PDF_DESCRIPTION_RE.match(title)
  if pdf_desc_match:
    title = pdf_desc_match.group(1)
  title = title.rstrip("( ,.")
  if title.endswith("(Redacted)"):
    title = title[:-10]
  if title.endswith("(SSI)"):
    title = title[:-5]
  title = title.rstrip("( ,.")
  if title == "DHS' Counterintelligence Activities Summary":
    title = "DHS' Counterintelligence Activities"
  report['url'] = report_url
  report['title'] = title

  timestamp = result.select("td")[2].text.strip()

  published_on = datetime.strptime(timestamp, "%m/%d/%Y")
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")

  report_id = result.select("td")[0].text.strip()
  # Audit numbers are frequently reused, so add the year to our ID
  report_id = "%s_%d" % (report_id, published_on.year)

  report['report_id'] = report_id

  # if component is a top-level DHS thing, file as 'dhs'
  # otherwise, the component is the agency for our purposes
  if component.startswith('dhs_'):
    report['agency'] = 'dhs'
  else:
    report['agency'] = component
  report['agency_name'] = COMPONENTS[component][1]

  return report


def url_for(options, component):
  return ("https://www.oig.dhs.gov/reports/audits-inspections-and-evaluations"
          "?field_dhs_agency_target_id={}"
          "&field_oversight_area=All"
          "&field_fy_value=All".format(COMPONENTS[component][0]))


# Component handle, with associated ID query string param
# Not every component is an agency. Some of these will be collapsed into 'dhs'
#   for a report's 'agency' field.
# Some additional info on DHS components: https://www.dhs.gov/department-components
COMPONENTS = {
  'secret_service': (8, "U.S. Secret Service"),
  'coast_guard': (7, "U.S. Coast Guard"),
  'uscis': (6, "U.S. Citizenship and Immigration Services"),
  'tsa': (5, "Transportation Security Administration"),
  'ice': (3, "Immigration and Customs Enforcement"),
  'fema': (2, "Federal Emergency Management Agency"),
  'cbp': (1, "Customs & Border Protection"),
  'dhs_other': (9, "Department of Homeland Security"),
  'dhs_mgmt': (4, "Department of Homeland Security"),
}

utils.run(run) if (__name__ == "__main__") else None
