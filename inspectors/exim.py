#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from datetime import datetime
import re

archive = 2007

def run(options):
  year_range = inspector.year_range(options, archive)

  published_on = None
  for page_url in [WHATS_NEW_URL, WHATS_NEW_ARCHIVE_URL, SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL]:
    body = utils.download(page_url)
    doc = BeautifulSoup(body)

    maincontent = doc.select("div#CS_Element_eximpagemaincontent")[0]
    after_maincontent = maincontent.nextSibling
    all_a = maincontent.find_all("a")

    for a in all_a:
      a_text = str(a.text)
      if a_text.strip() == "":
        continue

      a_href = a.get("href")
      if a_href.startswith("mailto:"):
        continue
      if a_href.startswith("https://public.govdelivery.com/"):
        continue
      if page_url == WHATS_NEW_URL and a_href == "/oig/whats-new-archive.cfm":
        # end of page
        break

      if deduplicate_url(a_href):
        continue

      all_text = a_text
      node = a.previous
      while True:
        if is_inside_link(node):
          break
        if isinstance(node, NavigableString):
          all_text = node + all_text
        node = node.previous
        if not node:
          break
        if node == maincontent:
          break

      # Response letters don't get their own date heading -- keep date from
      # last report and reuse in those cases
      temp = DATE_RE.search(all_text)
      if temp:
        # For semiannual reports to congress, use the second date from the text
        # Also, tack the date onto the report_id to disambiguate
        if page_url == SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL and a_text.strip().startswith('Semiannual Report to Congress'):
          a_text = a_text.strip() + ' ' + temp.group(0) + ' - '
          temp = DATE_RE.search(all_text, temp.end() + 1)
          a_text = a_text + temp.group(0)
        date_text = temp.group(0).replace('Sept ', 'Sep ')
        try:
          published_on = datetime.strptime(date_text, '%B %d, %Y')
        except ValueError:
          published_on = datetime.strptime(date_text, '%b %d, %Y')
      if published_on.year not in year_range:
        continue

      report = report_from(all_text, a_text, a_href, page_url, published_on)
      inspector.save_report(report)

  for page_url in [PRESS_RELEASES_URL, PRESS_RELEASES_ARCHIVE_URL]:
    done = False
    body = utils.download(page_url)
    doc = BeautifulSoup(body)

    maincontent = doc.select("div#CS_Element_eximpagemaincontent")[0]
    all_p = maincontent.find_all("p")

    for p in all_p:
      for all_text, link_text, link_url in recurse_tree(p, False):
        if link_url == None:
          continue
        if link_url.startswith("mailto:"):
          continue
        if page_url == WHATS_NEW_URL and link_url == "/oig/whats-new-archive.cfm":
          # end of page
          done = True
          break
        if link_url.startswith("https://public.govdelivery.com/"):
          continue
        for index_url in URLS:
          if index_url.find(link_url) != -1:
            continue

        if deduplicate_url(link_url):
          continue

        date_match = DATE_RE.search(all_text)
        try:
          date_text = date_match.group(0).replace('Sept ', 'Sep ')
          published_on = datetime.strptime(date_text, '%B %d, %Y')
        except ValueError:
          published_on = datetime.strptime(date_text, '%b %d, %Y')
        if published_on.year not in year_range:
          continue

        report = report_from(all_text, link_text, link_url, page_url, published_on)
        inspector.save_report(report)
      if done: break

def report_from(all_text, link_text, link_url, page_url, published_on):
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

  url_match = IDENTIFIER_RE_URL.search(link_url)
  text_match = IDENTIFIER_RE_TEXT.search(all_text)
  if url_match:
    report_id = url_match.group(1)
  elif text_match:
    report_id = text_match.group(1)
  elif link_url.rfind("loader.cfm") == -1:
    report_id = link_url[link_url.rfind('/') + 1 : link_url.rfind('.')]
  else:
    # we could get the server's filename from the Content-Disposition header
    # but that would require hitting the network and lots of parsing
    report_id = link_text
  # clip report_id if it gets too long
  report_id = report_id[:100]

  if link_url.endswith(".pdf"):
    file_type = "pdf"
  elif link_url.find("loader.cfm") != -1:
    file_type = "pdf"
  elif link_url.endswith(".cfm") or link_url.endswith(".htm") or link_url.endswith(".html"):
    file_type = "htm"
  else:
    raise Exception("Unable to guess file type\n%s" % link_url)

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['url'] = link_url
  report['report_id'] = report_id
  report['title'] = link_text
  report['file_type'] = file_type

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
  accumulator = ["", "", None]
  for child in root.children:
    double_br = False
    if isinstance(child, Tag):
      if child.name == "br":
        if child.parent.name == "br":
          if child.parent.contents[0] == child:
            double_br = True
        temp = child
        while True:
          temp = temp.previous_element
          if isinstance(temp, NavigableString):
            if len(str(temp).strip()) > 0:
              break
          elif isinstance(temp, Tag):
            if temp.name == "br":
              double_br = True
              break
            if temp.name == "a":
              break
    if double_br:
      # Split up the results here, yield the accumulator contents so far
      # and reinitialize the accumulator
      yield tuple(accumulator)
      accumulator = ["", "", None]
    if isinstance(child, Tag):
      if child.name == "a":
        inside_link = True
        href = child.get("href")
        if accumulator[2] == None:
          accumulator[2] = href
        else:
          if accumulator[2] != href:
            # We have found a second link in one report section, so check it
            # against the whitelist of expected patterns. If the second link
            # doesn't match any of those, then throw an exception
            for whitelisted in SECOND_LINK_WHITELIST:
              if href.find(whitelisted) != -1:
                break
            else:
              # Check if there is a <a> with no text in it (i.e. only a <br>
              # tag) and if so, throw it away and accept the new link
              if len(accumulator[1].strip()) == 0:
                accumulator[2] = href
              else:
                raise Exception("Found two different URLs in one entry, something is wrong\n%s\n%s" % (accumulator[2], href))

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
            href = output[2]
            # We have found a second link in one report section, so check it
            # against the whitelist of expected patterns. If the second link
            # doesn't match any of those, then throw an exception
            for whitelisted in SECOND_LINK_WHITELIST:
              if href.find(whitelisted) != -1:
                break
            else:
              # Check if there is a <a> with no text in it (i.e. only a <br>
              # tag) and if so, throw it away and accept the new link
              if len(accumulator[1].strip()) == 0:
                accumulator[0] = accumulator[0] + output[0]
                accumulator[1] = output[1]
                accumulator[2] = output[2]
              else:
                raise Exception("Found two different URLs in one entry, something is wrong\n%s\n%s" % (accumulator[2], href))
    elif isinstance(child, NavigableString):
      accumulator[0] = accumulator[0] + str(child)
      if inside_link:
        accumulator[1] = accumulator[1] + str(child)
  yield tuple(accumulator)

def is_inside_link(node):
  x = node
  while x != None:
    if x.name == "a":
      return True
    x = x.parent
  return False

_url_dedup_set = set()
def deduplicate_url(url):
  '''Records all URLs passed. If a URL has been seen before, return True,
  or return False if this is the first time the URL has been seen'''

  if url.startswith('/'):
    url = "http://www.exim.gov" + url

  # At least two files are uploaded twice, once in /oig/uploads/ and once in
  # /oig/uploads/reports/, with the same name in each. Check both locations
  # for duplicates.
  if url in _url_dedup_set:
    return True
  if url.replace("http://www.exim.gov/oig/upload/", "http://www.exim.gov/oig/reports/upload/") in _url_dedup_set:
    return True
  if url.replace("http://www.exim.gov/oig/reports/upload/", "http://www.exim.gov/oig/upload/") in _url_dedup_set:
    return True

  _url_dedup_set.add(url)
  return False

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
  elif page_url == SEMIANNUAL_REPORTS_AND_TESTIMONIES_URL:
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

SECOND_LINK_WHITELIST = (
  "TEXT-ONLY",
  "/about/library/foia/foia-request-requirements.cfm",
  "/oig/pressreleases/Press-Releases-Archive.cfm"
)

DATE_RE = re.compile("(January|February|March|April|May|June|July|August|" +
                    "September|October|November|December|" +
                    "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)" +
                    "\\s+([123]?[0-9]),\\s+" +
                    "(20[0-9][0-9])")

IDENTIFIER_RE_TEXT = re.compile("""\((OIG-[A-Z][A-Z]-[0-9][0-9]-[0-9][0-9])\)""")
IDENTIFIER_RE_URL = re.compile("""(OIG-[A-Z][A-Z]-[0-9][0-9]-[0-9][0-9])""")

utils.run(run) if (__name__ == "__main__") else None
