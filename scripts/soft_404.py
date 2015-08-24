#!/usr/bin/env python

import os, os.path
import re
from inspectors.utils import utils
import logging
import scrapelib

PAGE_NOT_FOUND_PATTERN = b"(<title>(404 Page Not Found - CFTC|CPB: Page Not Found|DoD IG - Error Message|404: NOT FOUND|Page Not Found|Maintenance|Page Not Found Smithsonian|404)</title>|That page was not found\\.&#160; If possible we will redirect you to that content now\\.)"
PAGE_NOT_FOUND_BYTES_RE = re.compile(PAGE_NOT_FOUND_PATTERN)
PAGE_NOT_FOUND_STRING_RE = re.compile(PAGE_NOT_FOUND_PATTERN.decode('ascii'))

URLS = {
  'cftc': 'http://www.cftc.gov/About/OfficeoftheInspectorGeneral/doesyour404work',
  'cpb': 'http://www.cpb.org/oig/doesyour404work',
  'dod': 'http://www.dodig.mil/doesyour404work',
  'fec': 'http://www.fec.gov/fecig/doesyour404work',
  'gpo': 'http://www.gpo.gov/oig/doesyour404work',
  'ncua': 'http://www.ncua.gov/about/Leadership/Pages/doesyour404work',
  'smithsonian': 'http://www.si.edu/OIG/doesyour404work',
}

IGS_WITH_BAD_404 = tuple(URLS.keys())

def run(options):

  ig_list = options.get("inspectors")

  for inspector, url in URLS.items():
    if (not ig_list) or (inspector in ig_list):
      logging.debug("[%s] Checking..." % inspector)
      result = None
      status_code_rewritten = False
      while True:
        try:
          response = utils.scraper.get(url)
          result = response.text
          break
        except scrapelib.HTTPError as e:
          if e.response.status_code == 404:
            status_code_rewritten = True
            if 'location' in e.response.headers:
              url = e.response.headers['location']
              continue
          result = e.body
          break

      if not status_code_rewritten:
        print("False negative for %s (handler did not rewrite error code)" %
              inspector)

      match = PAGE_NOT_FOUND_STRING_RE.search(result)
      if not match:
        print("False negative for %s (regular expression did not match error "
              "page contents)" % inspector)

  data_dir = utils.data_dir()
  for inspector in os.listdir(data_dir):
    if (not ig_list or inspector in ig_list) and inspector in IGS_WITH_BAD_404:
      inspector_path = os.path.join(data_dir, inspector)
      if os.path.isdir(inspector_path):
        for dirpath, dirnames, filenames in os.walk(inspector_path):
          for filename in filenames:
            path = os.path.join(dirpath, filename)
            try:
              f = open(path, 'r', encoding='utf-8')
              for line in f:
                if PAGE_NOT_FOUND_STRING_RE.search(line):
                  print("Soft 404 found: %s" % path)
            except UnicodeDecodeError:
              f = open(path, 'rb')
              for line in f:
                if PAGE_NOT_FOUND_BYTES_RE.search(line):
                  print("Soft 404 found: %s" % path)
