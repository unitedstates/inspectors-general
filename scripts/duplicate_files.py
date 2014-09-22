#!/usr/bin/env python

import hashlib
import os, os.path
from inspectors.utils import utils
import logging

class Deduplicator(object):
  def __init__(self):
    self.hashes_to_names = {}

  def add_and_check_file(self, filename):
    hash = self.file_to_hash(filename)
    if hash in self.hashes_to_names:
      self.hashes_to_names[hash].append(filename)
      return self.hashes_to_names[hash]
    else:
      self.hashes_to_names[hash] = [filename]
      return None

  def file_to_hash(self, path):
    hash = hashlib.sha256()
    with open(path, 'rb') as f:
      message = None
      while message != b'':
        message = f.read(1024 * 1024)
        hash.update(message)
    return hash.digest()

def run(options):
  ig_list = options.get("inspectors")

  dedup = Deduplicator()
  data_dir = utils.data_dir()
  for inspector in os.listdir(data_dir):
    if not ig_list or inspector in ig_list:
      logging.debug("[%s] Checking..." % inspector)

      inspector_path = os.path.join(data_dir, inspector)
      if os.path.isdir(inspector_path):
        for dirpath, dirnames, filenames in os.walk(inspector_path):
          for filename in filenames:
            result = dedup.add_and_check_file(os.path.join(dirpath, filename))
            if result:
              print("Duplicate files: " + ", ".join(result))

def main():
  import sys, os, os.path
  sys.path.append(os.getcwd())
  sys.path.append(os.path.abspath(".."))
  run([])
main() if (__name__ == "__main__") else None
