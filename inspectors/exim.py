#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import utils, inspector
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from datetime import datetime
import re

def run(options):
  year_range = inspector.year_range(options)
  for page_url in URLS:
    body = utils.download(page_url)
    doc = BeautifulSoup(body)
    maincontent = doc.select("div#CS_Element_eximpagemaincontent")[0]
    all_p = maincontent.find_all("p")
    for p in all_p:
      for all_text, link_text, link_url in recurse_tree(p, False):
        if link_url == None:
          continue
        if link_url.startswith('mailto:'):
          continue
        year = DATE_RE.search(all_text).group(3)
        if int(year) not in year_range:
          continue
        report = report_from(all_text, link_text, link_url, page_url)
        inspector.save_report(report)

def report_from(all_text, link_text, link_url, page_url):
  report = {
    'inspector': 'exim',
    'inspector_url': 'http://www.exim.gov/oig/index.cfm',
    'agency': 'exim',
    'agency_name': 'Export-Import Bank of the United States'
  }

  link_text = link_text.strip()
  if link_url.startswith('/'):
    link_url = "http://www.exim.gov" + link_url

  all_text = all_text.strip()
  report_type = type_for(page_url, all_text)

  date_text = DATE_RE.search(all_text).group(0)
  published_on = datetime.strptime(date_text, '%B %d, %Y')

  report_match = IDENTIFIER_RE.search(all_text)
  if report_match:
    report_id = report_match.group(1)
  else:
    report_id = link_url[link_url.rfind('/') + 1 : link_url.rfind('.')]

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['url'] = link_url
  report['report_id'] = report_id
  report['title'] = link_text

  return report

# Recurse through a subtree of the DOM, collect all the text, link text, and
# link URLs in the subtree. If there are two <br>s in a row, split up the
# collected text, with the <br><br> as a boundary. This yields multiple tuples,
# each of the format (all_text, link_text, link_url). Raises an exception if
# one section has multiple links with different hrefs.
# It is the responsibility of the caller to do any final filtering on the
# results, such as throwing out any tuples without a link, or throwing out
# mailto: links.
def recurse_tree(root, inside_link):
  last_node_was_br = False
  accumulator = ["", "", None]
  for child in root.children:
    if isinstance(child, Tag) and child.name == "br":
      if last_node_was_br:
        # Split up the results here, yield the accumulator contents so far
        # and reinitialize the accumulator
        yield tuple(accumulator)
        accumulator = ["", "", None]
        last_node_was_br = False
      else:
        last_node_was_br = True
    else:
      last_node_was_br = False
    if isinstance(child, Tag):
      if child.name == "a":
        inside_link = True
        if accumulator[2] == None:
          accumulator[2] = child.get("href")
        else:
          if accumulator[2] != child.get("href"):
            raise Exception("Found two different URLs in one entry, something is wrong\n%s\n%s" % (accumulator[2], child.get("href")))

      # Concatenate first result out of generator with all text so far.
      # If there's more than one result out of the generator, yield the previous
      # accumulator value and copy the result into the accumulator.
      # At the end, the last output from recursion should be in the accumulator,
      # ready to add text from the rest of this level of the tree.
      # If the node has no children, none of this code does anything, and the
      # accumulator stays the same, and we keep collecting text later.
      # If the node's subtree yields one result, just add it to the accumulator
      # and keep going without yielding a complete result yet
      generator = recurse_tree(child, inside_link)
      first = True
      for output in generator:
        if not first:
          yield tuple(accumulator)
          accumulator = ["", "", None]
        first = False
        accumulator[0] = accumulator[0] + output[0]
        accumulator[1] = accumulator[1] + output[1]
        if accumulator[2] == None:
          accumulator[2] = output[2]
        elif output[2] == None:
          pass
        else:
          if accumulator[2] != output[2]:
            raise Exception("Found two different URLs in one entry, something is wrong\n%s\n%s" % (accumulator[2], output[2]))
    elif isinstance(child, NavigableString):
      accumulator[0] = accumulator[0] + str(child)
      if inside_link:
        accumulator[1] = accumulator[1] + str(child)
  yield tuple(accumulator)

def type_for(page_url, text):
  if page_url == WHATS_NEW_URL or page_url == WHATS_NEW_ARCHIVE_URL:
    if text.find("Semiannual Report to Congress") != -1:
      return "other"
    header = text[:text.find(' - ')]
    if header == "Testimony":
      return "testimony"
    if header == "Report":
      return "audit"
    if header == "Press Report":
      return "press"
    return "other"
  elif page_url == PRESS_RELEASES_URL or page_url == PRESS_RELEASES_ARCHIVE_URL:
    return "press"
  elif page_url == SEMIANNUAL_REPORTS_AND_TESTIMONIES:
    if text.find("House") != -1 or text.find("Senate") != -1:
      return "testimony"
    return "other"

WHATS_NEW_URL = "http://www.exim.gov/oig/index.cfm"
WHATS_NEW_ARCHIVE_URL = "http://www.exim.gov/oig/whats-new-archive.cfm"
PRESS_RELEASES_URL = "http://www.exim.gov/oig/pressreleases/"
PRESS_RELEASES_ARCHIVE_URL = "http://www.exim.gov/oig/pressreleases/Press-Releases-Archive.cfm"
SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL = "http://www.exim.gov/oig/reports/semiannual-reports-and-testimony.cfm"

URLS = (
  WHATS_NEW_URL,
  WHATS_NEW_ARCHIVE_URL,
  PRESS_RELEASES_URL,
  PRESS_RELEASES_ARCHIVE_URL,
  SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL
)

DATE_RE = re.compile("(January|February|March|April|May|June|July|August|" +
                    "September|October|November|December) ([123]?[0-9]), " +
                    "(20[0-9][0-9])")

IDENTIFIER_RE = re.compile("""\((OIG-[A-Z][A-Z]-[0-9][0-9]-[0-9][0-9])\)""")

utils.run(run) if (__name__ == "__main__") else None
