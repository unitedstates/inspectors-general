#!/usr/bin/env python

import os, os.path
import re

PAGE_NOT_FOUND_RE = re.compile(b"(<title>(404 Page Not Found - CFTC|CPB: Page Not Found|DoD IG - Error Message|404: NOT FOUND|Page Not Found|Maintenance|Page Not Found Smithsonian|404)</title>|That page was not found\\.&#160; If possible we will redirect you to that content now\\.|The Office of Inspector General [(]OIG[)] is an independent unit established by law which is responsible for promoting economy, efficiency, and effectiveness and detecting and preventing fraud, waste, and mismanagement in the General Services Administration's [(]GSA[)] programs and operations\\.)")

IGS_WITH_BAD_404 = (
  'cftc',
  'cpb',
  'dod',
  'exim',
  'fec',
  'gpo',
  'gsa',
  'ncua',
  'smithsonian',
  'state'
)

def run(ig_list):
  from inspectors.utils import utils
  data_dir = utils.data_dir()
  for inspector in os.listdir(data_dir):
    if (not ig_list or inspector in ig_list) and inspector in IGS_WITH_BAD_404:
      inspector_path = os.path.join(data_dir, inspector)
      if os.path.isdir(inspector_path):
        for dirpath, dirnames, filenames in os.walk(inspector_path):
          for filename in filenames:
            path = os.path.join(dirpath, filename)
            f = open(path, 'rb')
            for line in f:
              if PAGE_NOT_FOUND_RE.search(line):
                print("Soft 404 found: %s" % path)
