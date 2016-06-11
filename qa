#!/usr/bin/env python

import sys
import os
import os.path
import io

from inspectors.utils import utils
from inspectors.utils import admin

def main():
  cwd = os.getcwd()
  scripts_dir = os.path.join(cwd, 'scripts')
  if not os.path.isdir(scripts_dir):
    qa_dir = os.path.dirname(sys.argv[0])
    scripts_dir = os.path.join(qa_dir, 'scripts')
  if not os.path.isdir(scripts_dir):
    print("Could not find the scripts directory. Try running again from the "\
        "same directory that 'qa' is in.")
    sys.exit(1)
  sys.path.append(scripts_dir)

  script_names = []
  for file in os.listdir(scripts_dir):
    file_path = os.path.join(scripts_dir, file)
    if os.path.isfile(file_path):
      name, extension = os.path.splitext(file)
      if extension == ".py":
        script_names.append(name)

  script_names.sort()
  script_names_joined = ",".join(script_names)

  def print_help():
    print("Usage: qa {all,%s} [--only=dod,epa,gao,nasa,...] [--safe] [--help]"%\
        (script_names_joined))

  ig_list = []
  opts = utils.options()
  if "safe" in opts:
    ig_list = utils.safe_igs()
  elif "only" in opts:
    ig_list = opts["only"].split(",")

  successful = True

  all = "all" in sys.argv
  if "help" in opts or "help" in sys.argv:
    print_help()
  else:
    ran_one = False

    total_report = ""

    for script_name in script_names:
      if all or script_name in sys.argv:
        print("Running %s..." % script_name)
        ran_one = True


        # captures STDOUT during script run,
        # depends on using print() and not logging.warn()
        saved_stdout = sys.stdout
        stringio = io.StringIO()
        sys.stdout = stringio

        run_method = __import__(script_name).run
        utils.run(run_method, {'inspectors': ig_list})

        sys.stdout = saved_stdout
        value = stringio.getvalue()
        if value:
          total_report += ('QA results for `%s`:\n\n%s\n\n' % (script_name, value))
          successful = False

    if not ran_one:
      print_help()

    if successful:
      exit(0)
    else:
      admin.log_qa(total_report)
      exit(1)

main()
