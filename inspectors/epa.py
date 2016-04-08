#!/usr/bin/env python

import datetime
from urllib.parse import urljoin
import re
import os.path
from utils import utils, inspector

archive = 1996

# options:
#   standard since/year options for a year range to fetch from.

RE_YEAR = re.compile(r'\d{4} (?:OIG )?Reports')
RE_DATE = re.compile('(?:(?:Jan|January|JANUARY|Feb|February|FEBRUARY|Mar|'
                     'March|MARCH|Apr|April|APRIL|May|MAY|June|JUNE|July|JULY|'
                     'Aug|August|AUGUST|Sept|September|SEPTEMBER|'
                     'Oct|October|OCTOBER|Nov|November|NOVEMBER|'
                     'Dec|December|DECEMBER)'
                     ',?(?:\\s+[0-9I]{1,2}\\s*,)?\\s*[0-9]{4})|'
                     '[0-9]{2}/[0-9]{2}/[0-9]{4}')
BASE_URL = "http://www.epa.gov/office-inspector-general/"
REPORTS_LATEST_URL = BASE_URL + "oig-reports"
REPORTS_YEAR_URL_FORMAT = BASE_URL + "%d-reports"
REPORTS_1999_1996_URL = BASE_URL + "1999-1996-reports"
REPORTS_2015_URL = BASE_URL + "2015-oig-reports"
DATE_FORMATS = [
  '%b %d, %Y',
  '%B %d, %Y',
  '%b %d,%Y',
  '%B %d,%Y',
  '%b %d , %Y',
  '%B %d , %Y',
  '%b, %d, %Y',
  '%B, %d, %Y',
  '%b %d %Y',
  '%B %d %Y',
  '%b %Y',
  '%B %Y',
  '%m/%d/%Y',
]
REPORT_PUBLISHED_MAPPING = {
  "http://www.epa.gov/sites/production/files/2015-09/documents/9p00210.pdf":
    datetime.datetime(1999, 6, 30),
  "http://www.epa.gov/sites/production/files/2015-09/documents/20090806-09-p-0203.pdf":
    datetime.datetime(2009, 8, 6),
}
REPORT_ID_MAPPING = {
  "http://www.epa.gov/sites/production/files/2015-09/documents/9p00210.pdf":
    "99P00210",
  "http://www.epa.gov/sites/production/files/2015-09/documents/20090806-09-p-0203.pdf":
    "09-P-0203",
}


def run(options):
  year_range = inspector.year_range(options, archive)

  report_seen_flag = False
  for url in years_to_index_urls(year_range):
    index = utils.beautifulsoup_from_url(url)
    tables = index.find_all("table")
    lis = index.select("ul.field li")
    if len(tables) == 1:
      table = tables[0]
      trs = table.select('tr')
      for tr in trs:
        tds = tr.select('td')
        if not tds:
          continue
        if RE_YEAR.match(tds[0].text):
          continue
        report_seen_flag = True

        try:
          published_on_dt = parse_date(tds[0].text.strip())
        except Exception:
          pass
        if not published_on_dt:
          try:
            published_on_dt = parse_date(tds[2].text.strip())
          except Exception:
            pass
        if not published_on_dt:
          inspector.log_no_date(tds[2].text, tds[1].text)
          continue
        if published_on_dt.year not in year_range:
          continue

        report = report_from_table(tds, published_on_dt, url)
        if report:
          inspector.save_report(report)
    else:
      for li in lis:
        report_seen_flag = True
        date_match = RE_DATE.search(li.text)
        if date_match:
          published_on_dt = parse_date(date_match.group())
        else:
          href = urljoin(url, li.a["href"])
          if href in REPORT_PUBLISHED_MAPPING:
            published_on_dt = REPORT_PUBLISHED_MAPPING[href]
        if not published_on_dt:
          inspector.log_no_date(extract_url(li), li.a.text, href)
          continue
        if published_on_dt.year not in year_range:
          continue

        report = report_from_list(li, published_on_dt, url)
        if report:
          inspector.save_report(report)

    if not report_seen_flag:
      raise inspector.NoReportsFoundError("EPA")


RE_PDF = re.compile('PDF', re.I)

def report_from_table(tds, published_on_dt, base_url):
  report = {
    'inspector': 'epa',
    'inspector_url': 'http://www.epa.gov/oig',
    'agency': 'epa',
    'agency_name': 'Environmental Protection Agency',
    'summary_only': False
  }

  report_url = extract_url(tds[1])
  if report_url:
    report_url = urljoin(base_url, report_url)

  if not report_url:
    raise Exception("Couldn't find a link for report!")


  report_id = re.sub("\s+", " ", tds[2].text).strip()
  # fix typo
  if report_id == "May 17, 2006":
    report_id = None
  # fallback
  if (report_id == "") or (not report_id):
    report_id, extension = os.path.splitext(report_url.split("/")[-1])

  published_on = datetime.datetime.strftime(published_on_dt, '%Y-%m-%d')

  # Don't take all the text because it can sometimes include a <br> and some
  # annotation.
  title = tds[1].a.text.strip()

  report.update({
    'report_id': report_id,
    'title': title,
    'published_on': published_on
  })

  # some reports only have the At A Glance summary,
  # e.g. when the full report is technical/sensitive
  if report_url.endswith("_glance.pdf"):
    report['summary_only'] = True
    report['unreleased'] = True
    report['summary_url'] = report_url
  elif not report_url.endswith(".pdf"):
    report['landing_url'] = report_url
    landing_page = utils.beautifulsoup_from_url(report_url)
    doc_links = landing_page.select("span.file a.file-link")
    for doc_link in doc_links:
      absolute_href = urljoin(report_url, doc_link["href"])
      text = doc_link.text
      if "Report At A Glance" in text or "Report At a Glance" in text:
        report['summary_url'] = absolute_href
      elif ("Full Report" in text or
            "Full Semiannual Report" in text or
            "Full Compendium" in text or
            "Full Document" in text or
            "Key Management Challenges Memorandum" in text):
        report['url'] = absolute_href
      elif ("Response to Report" in text or
            "IG Comment on" in text and "Response" in text or
            "Response to OIG Report" in text or
            "Report Briefing with Gallery" in text or
            "Dispute Resolution" in text or
            "Materials Relating to" in text or
            "Addendum" in text or
            "Press Statement" in text or
            "Detailed Comments" in text or
            text.startswith("Attachment") or
            "In Response to" in text or
            "Full Resolution Materials" in text or
            "Podcast Transcript" in text):
        pass
      else:
        raise Exception("Unrecognized document link: %s" % doc_link.text)
    if report.get('summary_url') and not report.get('url'):
      report['summary_only'] = True
      report['unreleased'] = True
    what_we_found = landing_page.find("strong", text=["What We Found",
                                                      "What Was Found",
                                                      "What the Firm Found"])
    message_to_congress = landing_page.find("h2", text="Message to Congress")
    if what_we_found:
      summary = what_we_found.parent.find_next_sibling("p").text.strip()
      report['summary'] = summary
    elif message_to_congress:
      summary = message_to_congress.find_next_sibling("p").text.strip()
      report['summary'] = summary
    elif "annual-plan-fiscal-year-" in report_url:
      report['summary'] = landing_page.article.p.text.strip()
    elif "annual-superfund-report-" in report_url:
      report['summary'] = landing_page.article.find_all("a")[1].text.strip()
    else:
      raise Exception("No report summary was found on %s" % report_url)
  else:
    report['url'] = report_url

  return report

def report_from_list(li, published_on_dt, base_url):
  report = {
    'inspector': 'epa',
    'inspector_url': 'http://www.epa.gov/oig',
    'agency': 'epa',
    'agency_name': 'Environmental Protection Agency',
    'summary_only': False
  }

  report_url = extract_url(li)
  if report_url:
    report_url = urljoin(base_url, report_url)

  if not report_url:
    raise Exception("Couldn't find a link for report!")

  fileinfo = li.find("span", class_="fileinfo").text
  published_on = datetime.datetime.strftime(published_on_dt, '%Y-%m-%d')
  title = li.a.text.strip()

  if report_url in REPORT_ID_MAPPING:
    report_id = REPORT_ID_MAPPING[report_url]
  else:
    date_match = RE_DATE.search(fileinfo)
    report_id = fileinfo[date_match.end():].lstrip(", \n").rstrip(") \n")

  if not report_id:
    title_slug = re.sub(r'\W', '', title[:16])
    report_id = (published_on + '-' + title_slug)

  report.update({
    'report_id': report_id,
    'title': title,
    'published_on': published_on
  })

  # some reports only have the At A Glance summary,
  # e.g. when the full report is technical/sensitive
  if report_url.endswith("_glance.pdf"):
    report['summary_only'] = True
    report['unreleased'] = True
    report['summary_url'] = report_url
    report['landing_url'] = base_url
  else:
    report['url'] = report_url

  return report

def extract_url(td):
  url = None
  links = td.select('a')
  links = [link for link in links
           if not "/office-inspector-general/multimedia" in link['href']
           and not "/office-inspector-general/oig-multimedia" in link['href']]
  if len(links) == 1:
    url = links[0]['href']
  elif len(links) == 2 and links[0]['href'] == links[1]['href']:
    url = links[0]['href']
  else:
    pdf_links = [link for link in links if RE_PDF.search(link.text)]
    if pdf_links:
      url = pdf_links[0]['href']
  return url


_latest_year = None


def years_to_index_urls(year_range):
  global _latest_year
  if _latest_year is None:
    doc = utils.beautifulsoup_from_url(REPORTS_LATEST_URL)
    for ul in doc.select("ul.pipeline"):
      if ul.li and ul.li.a:
        link_text = ul.li.a.text.strip()
        if link_text.isdigit():
          _latest_year = int(link_text)
  if _latest_year is None:
    raise Exception("Could not find \"Reports by Year\" links")

  urls = set([REPORTS_LATEST_URL])
  for year in year_range:
    if year <= 1999:
      urls.add(REPORTS_1999_1996_URL)
    elif year == 2015:
      urls.add(REPORTS_2015_URL)
    elif year >= _latest_year:
      pass
    else:
      urls.add(REPORTS_YEAR_URL_FORMAT % year)

  urls = list(urls)
  urls.sort()
  return urls

def parse_date(text):
  text = text.replace("Sept ", "Sep ")
  text = text.replace("I5", "15")
  text = re.sub("\\s+", " ", text)
  for date_format in DATE_FORMATS:
    try:
      return datetime.datetime.strptime(text, date_format)
    except ValueError:
      pass
  return None

utils.run(run) if (__name__ == "__main__") else None
