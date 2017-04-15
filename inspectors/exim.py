#!/usr/bin/env python

from utils import utils, inspector, admin
from datetime import datetime
from urllib.parse import urljoin
import os.path
import re

archive = 2007


def run(options):
  year_range = inspector.year_range(options, archive)

  for page_url in URLS:
    doc = utils.beautifulsoup_from_url(page_url)

    articles = doc.find_all("article")
    if len(articles) > 1:
      raise Exception("More than one article found on %s" % page_url)
    maincontent = articles[0]
    all_a = maincontent.find_all("a")
    if not all_a:
      raise inspector.NoReportsFoundError("Ex-Im Bank (%s)" % page_url)
    for a in all_a:
      a_text = str(a.text)
      if a_text.strip() == "":
        continue

      if a_text == "Text Only Version":
        continue

      a_href = a.get("href")
      if a_href.startswith("mailto:"):
        continue
      if a_href.startswith("https://public.govdelivery.com/"):
        continue

      paragraph = a.parent
      while paragraph.name != "p":
        paragraph = paragraph.parent
      all_text = paragraph.text.strip()

      # Response letters don't get their own date heading -- keep date from
      # last report and reuse in those cases
      temp = DATE_RE.search(all_text)
      published_on = None
      if temp:
        date_text = temp.group(0).replace("Sept ", "Sep ")
        try:
          published_on = datetime.strptime(date_text, '%B %d, %Y')
        except ValueError:
          pass
        if published_on is None:
          try:
            published_on = datetime.strptime(date_text, '%b %d, %Y')
          except ValueError:
            pass
        if published_on is None:
          try:
            published_on = datetime.strptime(date_text, '%b %d,%Y')
          except ValueError:
            pass
      if published_on is None:
        date_text = paragraph.find_previous_sibling("p").text.strip()
        date_text = date_text.replace("Sept ", "Sep ")
        try:
          published_on = datetime.strptime(date_text, '%b %d, %Y')
        except ValueError:
          pass
      if published_on and published_on.year not in year_range:
        continue

      report = report_from(all_text, a_text, a_href, page_url, published_on, paragraph)
      if report:
        inspector.save_report(report)


def report_from(all_text, link_text, link_url, page_url, published_on, paragraph):
  report = {
    'inspector': 'exim',
    'inspector_url': 'http://www.exim.gov/about/oig',
    'agency': 'exim',
    'agency_name': 'Export-Import Bank of the United States'
  }

  link_text = link_text.strip()
  link_url = urljoin(page_url, link_url)

  all_text = all_text.strip()
  report_type = type_for(page_url, all_text, paragraph)

  url_match = IDENTIFIER_RE_URL.search(link_url)
  text_match = IDENTIFIER_RE_TEXT.search(all_text)
  if url_match:
    report_id = url_match.group(1)
  elif text_match:
    report_id = text_match.group(1)
  elif (page_url == PRESS_RELEASES_URL or
        page_url == INSPECTIONS_EVALUATIONS_SPECIAL_REPORTS_URL):
    report_id = link_text.replace(":", "")
  elif page_url == SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL:
    report_id = os.path.splitext(link_text)[0]
  elif (page_url == AUDIT_REPORTS_URL and
        paragraph.find_previous_sibling("h2").text == "Peer Review Reports"):
    report_id = link_text
  else:
    raise Exception("No report ID found for %r" % link_text)
  # clip report_id if it gets too long
  report_id = report_id[:100]

  if published_on is None:
    admin.log_no_date("exim", report_id, link_text, link_url)
    return

  if link_url.endswith(".pdf"):
    file_type = "pdf"
  elif link_url.endswith(".docx"):
    file_type = "docx"
  elif link_url.endswith((".htm", ".html")):
    file_type = "htm"
  elif link_url.endswith(".cfm"):
    file_type = "htm"
    report['unreleased'] = True
    report['missing'] = True
  elif not os.path.splitext(os.path.basename(link_url))[1]:
    file_type = "htm"
  else:
    raise Exception("Unable to guess file type\n%r" % link_url)

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['url'] = link_url
  report['report_id'] = report_id
  report['title'] = link_text
  report['file_type'] = file_type

  return report


def type_for(page_url, text, paragraph):
  if page_url == PRESS_RELEASES_URL:
    return "press"
  elif page_url == AUDIT_REPORTS_URL:
    return "audit"
  elif page_url == SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL:
    if "House" in text or "Senate" in text:
      return "testimony"
    return "other"
  elif page_url == INSPECTIONS_EVALUATIONS_SPECIAL_REPORTS_URL:
    h3 = paragraph.find_previous_sibling("h3")
    if h3.text == "Inspection Reports":
      return "inspection"
    elif h3.text == "Evaluation Reports":
      return "evaluation"
    elif h3.text == "Special\u00a0Reports":
      return "other"
  raise Exception("Could not detect report type for %r on %s" % (text, page_url))

PRESS_RELEASES_URL = "http://www.exim.gov/about/oig/press-releases"
SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL = "http://www.exim.gov/about/oig/reports"
AUDIT_REPORTS_URL = "http://www.exim.gov/about/oig/reports/audit-reports"  # TODO
INSPECTIONS_EVALUATIONS_SPECIAL_REPORTS_URL = "http://www.exim.gov/about/oig/reports/inspections-and-special-reports"  # TODO

URLS = (
  PRESS_RELEASES_URL,
  SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL,
  AUDIT_REPORTS_URL,
  INSPECTIONS_EVALUATIONS_SPECIAL_REPORTS_URL,
)

DATE_RE = re.compile("(January|February|March|April|May|June|July|August|" +
                     "September|October|November|December|" +
                     "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)" +
                     "\\s+([123]?[0-9]),\\s*" +
                     "(20[0-9][0-9])")

IDENTIFIER_RE_TEXT = re.compile("\( ?(OIG[- ][A-Z]{2,3}-[0-9]{2}-[0-9]{2}[A-Z]?)\)")
IDENTIFIER_RE_URL = re.compile("(OIG-[A-Z]{2,3}-[0-9]{2}-[0-9]{2}[A-Z]?)")

utils.run(run) if (__name__ == "__main__") else None
