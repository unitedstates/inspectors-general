from utils import utils
import os
import re
import logging
import datetime
import urllib.parse

# Save a report to disk, provide output along the way.
#
# 1) download report to disk
# 2) extract text from downloaded report using report['file_type']
# 3) write report metadata to disk
#
# fields used: file_type, url, inspector, year, report_id
# fields added: report_path, text_path

def save_report(report):
  options = utils.options()

  # create some inferred fields, set defaults
  preprocess_report(report)

  # validate report will return True, or a string message
  validation = validate_report(report)
  if validation != True:
    raise Exception("[%s][%s][%s] Invalid report: %s\n\n%s" % (
      report.get('type'), report.get('published_on'), report.get('report_id'),
      validation, str(report)))

  logging.warn("[%s][%s][%s]" % (report['type'], report['published_on'], report['report_id']))

  if options.get('dry_run'):
    logging.warn('\tdry run: skipping download and extraction')
  elif report.get('unreleased', False) is True:
    logging.warn('\tno download/extraction of unreleased report')
  else:
    report_path = download_report(report)
    if not report_path:
      logging.warn("\terror downloading report: sadly, skipping.")
      return False

    logging.warn("\treport: %s" % report_path)

    page_count = extract_page_count(report)
    if page_count != None:
      logging.debug("\tpages: %i" % page_count)
    else:
      logging.debug("\tpages: ?")

    text_path = extract_report(report)
    logging.warn("\ttext: %s" % text_path)

  data_path = write_report(report)
  logging.warn("\tdata: %s" % data_path)

  return True


# Preprocess before validation, to catch cases where inference didn't work.
# So, fields may be absent at this time.
def preprocess_report(report):
  # not sure what I'm doing with this field yet
  if report.get("type") is None:
    report["type"] = "report"

  # if we have a date, but no explicit year, extract it
  if report.get("published_on") and (report.get('year') is None):
    report['year'] = year_from(report)

  # if we have a URL, but no explicit file type, try to detect it
  if report.get("url") and (report.get("file_type") is None):
    parsed = urllib.parse.urlparse(report['url'])
    split = parsed.path.split(".")
    if len(split) > 1:
      report['file_type'] = split[-1]

  # strip trailing spaces from common string fields,
  # but leave the presence check for the validate function
  common_strings = (
    "published_on", "report_id", "title", "inspector", "inspector_url",
    "agency", "agency_name", "url", "landing_url", "summary"
  )
  for field in common_strings:
    value = report.get(field)
    if (value is not None):
      report[field] = value.strip()


# Ensure required fields are present
def validate_report(report):
  required = (
    "published_on", "report_id", "title", "inspector", "inspector_url",
    "agency", "agency_name",
  )
  for field in required:
    value = report.get(field)
    if (value is None) or value.strip() == "":
      return "Missing a required field: %s" % field

  # A URL is required, unless 'unreleased' is set to True.
  url = report.get("url")
  if url is not None:
    if not url.startswith(("http://", "https://")):
      return "Report URL is not valid: %s" % url
    if report.get("file_type") is None:
      return "Couldn't figure out `file_type` from URL, please set it explicitly."
  else:
    if report.get('unreleased', False) is not True:
      return "Missing required field 'url' when field 'unreleased' != True"
    if report.get("landing_url") is None:
      return "Unreleased reports still need a landing_url"

  # If summary_url or landing_url are present, check those too.
  if report.get("landing_url"):
    if not report.get("landing_url").startswith(("http://", "https://")):
      return "Landing page URL is not valid: %s" % report.get("landing_url")
  if report.get("summary_url"):
    if not report.get("summary_url").startswith(("http://", "https://")):
      return "Summary URL is not valid: %s" % report.get("summary_url")

  # report_id can't have slashes, it'll mess up the directory structure
  if "/" in report["report_id"]:
    return "Invalid / in report_id - find another way: %r" % report["report_id"]

  if report.get("year") is None:
    return "Couldn't get `year`, for some reason."

  if report.get("type") is None:
    return "Er, this shouldn't happen: empty `type` field."

  try:
    datetime.datetime.strptime(report['published_on'], "%Y-%m-%d")
  except ValueError:
    return "Invalid format for `published_on`, must be YYYY-MM-DD."

  if re.search("(\\-\\d[\\-]|\\-\\d$)", report["published_on"]):
    return "Invalid format for `published_on`, dates must use zero prefixing."

  return True


def download_report(report):
  report_path = path_for(report, report['file_type'])
  binary = (report['file_type'].lower() == 'pdf')

  result = utils.download(
    report['url'],
    os.path.join(utils.data_dir(), report_path),
    {'binary': binary}
  )
  if result:
    return report_path
  else:
    return None

def extract_page_count(report):
  report_path = path_for(report, report['file_type'])
  real_report_path = os.path.join(utils.data_dir(), report_path)

  file_type_lower = report['file_type'].lower()
  if file_type_lower == "pdf":
    page_count = utils.page_count_from_pdf(report_path)
    if page_count != None:
      report['page_count'] = page_count
      return page_count
  elif file_type_lower == "htm" or file_type_lower == "html":
    return None
  else:
    logging.warn("Unknown file type, don't know how to extract page count!")
    return None

# relies on putting text next to report_path
def extract_report(report):
  report_path = path_for(report, report['file_type'])

  file_type_lower = report['file_type'].lower()
  if file_type_lower == "pdf":
    return utils.text_from_pdf(report_path)
  elif file_type_lower.startswith("htm"):
    return utils.text_from_html(report_path)
  else:
    logging.warn("Unknown file type, don't know how to extract text!")
    return None

def write_report(report):
  data_path = path_for(report, "json")

  utils.write(
    utils.json_for(report),
    os.path.join(utils.data_dir(), data_path)
  )
  return data_path


def path_for(report, ext):
  return os.path.join(report['inspector'], str(report['year']), report['report_id'], "report.%s" % ext)

def cache(inspector, path):
  return os.path.join(utils.cache_dir(), inspector, path)

# get year for a report from its publish date
def year_from(report):
  return int(report['published_on'].split("-")[0])

# assume standard options for IG scrapers, since/year
def year_range(options):
  this_year = datetime.datetime.now().year

  since = options.get('since')
  if type(since) is not str: since = None
  if since:
    since = int(since)
    if since > this_year:
      since = this_year

  year = options.get('year')
  if year:
    year = int(year)
    if year > this_year:
      year = this_year

  if since:
    year_range = list(range(since, this_year + 1))
  elif year:
    year_range = list(range(year, year + 1))
  else:
    year_range = list(range(this_year, this_year + 1))

  return year_range
