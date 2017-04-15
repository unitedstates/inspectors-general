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
    components = list(COMPONENTS.keys())

  report_id = options.get('report_id')

  limit = int(options.get('limit', 0))

  all_audit_reports = {}

  for component in components:
    logging.info("## Fetching reports for component %s" % component)
    url = url_for(options, component)
    doc = utils.beautifulsoup_from_url(url)

    results = doc.select("table.contentpaneopen table[border=1] tr")
    # accept only trs that look like body tr's (no 'align' attribute)
    #   note: HTML is very inconsistent. cannot rely on thead or tbody
    results = [x for x in results if x.get('align') is None]
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

  link = result.select("td")[2].select("a")[0]
  href = link['href'].replace("http://srvhq11c03-webs/", "/")
  href = href.replace("/assets/mgmt/", "/assets/Mgmt/")
  href = href.replace("/assets/mGMT/", "/assets/Mgmt/")
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

  timestamp = result.select("td")[0].text.strip()

  # can actually be just monthly, e.g. 12/03 (Dec 2003)
  if len(timestamp.split("/")) == 2:
    timestamp = "%s/01/%s" % tuple(timestamp.split("/"))

  # A date of '99' is also used when only the month and year are given
  # and no accurate date is available.
  if timestamp.split("/")[1] == "99":
    timestamp = "%s/01/%s" % (timestamp.split("/")[0], timestamp.split("/")[2])

  published_on = datetime.strptime(timestamp, "%m/%d/%y")
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")

  report_id = result.select("td")[1].text.strip()
  # A couple reports have no ID (Boston Marathon Bombing reports)
  if len(report_id) == 0:
    filename = urllib.parse.urlparse(report['url']).path.split("/")[-1]
    report_id = filename.split(".")[0]
  # Audit numbers are frequently reused, so add the year to our ID
  report_id = "%s_%d" % (report_id, published_on.year)

  # Discard these results, both the URLs and the report numbesr are correctly
  # listed in other entries
  if (report_id == "OIG-13-48_2013" and report_url ==
          "https://www.oig.dhs.gov/assets/Mgmt/2014/OIG_14-48_Mar14.pdf"):
    return
  if (report_id == "OIG-13-61_2013" and report_url ==
          "https://www.oig.dhs.gov/assets/Mgmt/2014/OIG_14-61_Apr14.pdf"):
    return
  if (report_id == "OIG-13-86_2013" and report_url ==
          "https://www.oig.dhs.gov/assets/Mgmt/2014/OIG_14-86_Apr14.pdf"):
    return

  # Fix typos in this report's date and number
  if (report_id == "OIG-12-105_2012" and report_url ==
          "https://www.oig.dhs.gov/assets/Mgmt/OIG_11-105_Aug11.pdf"):
    published_on = "2011-08-25"
    report['published_on'] = published_on
    report_id = "OIG-11-105_2011"

  report['report_id'] = report_id

  # if component is a top-level DHS thing, file as 'dhs'
  # otherwise, the component is the agency for our purposes
  if component.startswith('dhs_'):
    report['agency'] = 'dhs'
  else:
    report['agency'] = component
  report['agency_name'] = COMPONENTS[component][2]

  return report


def url_for(options, component):
  base = "https://www.oig.dhs.gov/index.php?option=com_content&view=article"
  return "%s&id=%s&Itemid=%s" % (base, COMPONENTS[component][0], COMPONENTS[component][1])


# Component handle, with associated ID and itemID query string params
#   Note: I believe only the ID is needed.
# Not every component is an agency. Some of these will be collapsed into 'dhs'
#   for a report's 'agency' field.
# Some additional info on DHS components: https://www.dhs.gov/department-components
COMPONENTS = {
  'secret_service': (58, 49, "U.S. Secret Service"),
  'coast_guard': (19, 48, "U.S. Coast Guard"),
  'uscis': (20, 47, "U.S. Citizenship and Immigration Services"),
  'tsa': (22, 46, "Transportation Security Administration"),
  'ice': (24, 44, "Immigration and Customs Enforcement"),
  'fema': (25, 38, "Federal Emergency Management Agency"),
  'cbp': (26, 37, "Customs & Border Protection"),
  'dhs_other': (59, 50, "Department of Homeland Security"),
  'dhs_mgmt': (23, 45, "Department of Homeland Security"),
  'dhs_cigie': (168, 150, "Council of the Inspectors General on Integrity and Efficiency"),
}

# 'Oversight areas' as organized by DHS. This is unused now, but
# could be used to run over the lists and associate a category with
# reports previously identified when running over each component.
# values are associated IT and itemID query strinhg params.
#   Note: I believe only the ID is needed.
AREAS = {
  'Border Security': (60, 30),
  'Counterterrorism': (61, 31),
  'Cybersecurity': (62, 32),
  'Disaster Preparedness, Response, Recovery': (63, 33),
  'Immigration': (64, 34),
  'Management': (33, 51),
  'Transportation Security': (66, 35),
}

utils.run(run) if (__name__ == "__main__") else None
