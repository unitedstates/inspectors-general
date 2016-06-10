from utils import utils
import os
import re
import logging
import datetime
import urllib.parse
import inspect

from . import admin
# Save a report to disk, provide output along the way.
#
# 1) download report to disk
# 2) extract text from downloaded report using report['file_type']
# 3) write report metadata to disk
#
# fields used: file_type, url, inspector, year, report_id
# fields added: report_path, text_path

def save_report(report):
  caller_filename = inspect.stack()[1][1]
  caller_scraper = os.path.splitext(os.path.basename(caller_filename))[0]

  options = utils.options()

  # create some inferred fields, set defaults
  preprocess_report(report)

  # validate report will return True, or a string message
  validation = validate_report(report)
  if validation != True:
    raise Exception("[%s][%s][%s] Invalid report: %s\n\n%s" % (
      report.get('type'), report.get('published_on'), report.get('report_id'),
      validation, str(report)))

  check_uniqueness(report['inspector'], report['report_id'], report['year'],
                   caller_scraper)

  logging.warn("[%s][%s][%s]" % (report['type'], report['published_on'], report['report_id']))

  if options.get('dry_run'):
    logging.warn('\tdry run: skipping download and extraction')
    if (not options.get('quick')) and report.get('url'):
      utils.check_report_url(report['url'])
  elif report.get('unreleased', False) is True:
    logging.warn('\tno download/extraction of unreleased report')
  else:
    report_path = download_report(report)
    if not report_path:
      logging.warn("\terror downloading report: sadly, skipping.")
      return False

    logging.warn("\treport: %s" % report_path)

    metadata = extract_metadata(report)
    if metadata:
      for key, value in metadata.items():
        logging.debug("\t%s: %s" % (key, value))

    text_path = extract_report(report)
    logging.warn("\ttext: %s" % text_path)

  data_path = write_report(report)
  logging.warn("\tdata: %s" % data_path)

  admin.log_report(caller_scraper)
  return True


# Preprocess before validation, to catch cases where inference didn't work.
# So, fields may be absent at this time.
def preprocess_report(report):
  # not sure what I'm doing with this field yet
  if report.get("type") is None:
    report["type"] = "report"

  # strip trailing spaces from common string fields,
  # but leave the presence check for the validate function
  common_strings_strip = (
    "inspector_url", "url", "landing_url", "file_type"
  )
  for field in common_strings_strip:
    value = report.get(field)
    if (value is not None):
      report[field] = value.strip()

  # sanitize common string fields (strip extra spaces, normalize magic quotes,
  # normalize dashes to hyphens, etc.)
  common_strings_sanitize = (
    "published_on", "report_id", "title", "inspector", "agency", "agency_name",
    "summary"
  )
  for field in common_strings_sanitize:
    value = report.get(field)
    if (value is not None):
      report[field] = sanitize(value)

  # if we have a date, but no explicit year, extract it
  if report.get("published_on") and (report.get('year') is None):
    report['year'] = year_from(report)

  # wipe line breaks from URLs (yes, this happens)
  if report.get("url"):
    report['url'] = re.sub("[\n\r]*", "", report['url'])

  # if we have a URL, but no explicit file type, try to detect it
  if report.get("url") and (report.get("file_type") is None):
    parsed = urllib.parse.urlparse(report['url'])
    split = parsed.path.split(".")
    if len(split) > 1:
      report['file_type'] = split[-1].lower()

ORD_A_LC = ord('a')
ORD_Z_LC = ord('z')
ORD_A_UC = ord('A')
ORD_Z_UC = ord('Z')
ORD_0 = ord('0')
ORD_9 = ord('9')

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

    for character in report.get(field):
      c = ord(character)
      if ORD_A_LC <= c and c <= ORD_Z_LC:
        break
      if ORD_A_UC <= c and c <= ORD_Z_UC:
        break
      if ORD_0 <= c and c <= ORD_9:
        break
    else:
      return "A required field doesn't contain any alphanumeric characters: " \
        "%s, %s" % (field, repr(report.get(field)))

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
  for character in str.join("", invalid_chars()):
    if character in report["report_id"]:
      return "Invalid %s in report_id - find another way: %r" % (character, report["report_id"])

  if report.get("year") is None:
    return "Couldn't get `year`, for some reason."

  if report.get("type") is None:
    return "Er, this shouldn't happen: empty `type` field."

  try:
    when = datetime.datetime.strptime(report['published_on'], "%Y-%m-%d")
    if when > datetime.datetime.now() + datetime.timedelta(weeks=1):
      return "Date in `published_on` is in the future."
  except ValueError:
    return "Invalid format for `published_on`, must be YYYY-MM-DD."

  if re.search("(\\-\\d[\\-]|\\-\\d$)", report["published_on"]):
    return "Invalid format for `published_on`, dates must use zero prefixing."

  return True

_uniqueness_storage_disk = {}
_uniqueness_storage_runtime = {}
def check_uniqueness(inspector, report_id, report_year, scraper):
  '''Given the name of an inspector, the ID of a report, and the year of the
  report, this function will check whether a duplicate report_id exists on-disk
  under a different year, or whether a duplicate report_id has been saved this
  session, in the same year or any other year. The index of reports already
  saved is lazily built on the first call from each inspector. Duplicate
  reports detected here will be collected, and a summary will be sent via
  admin.notify().'''

  # Be conservative, don't allow report_id to only differ in case
  report_id = report_id.lower()

  # Lazily set up data structures and read existing IDs from disk
  if inspector not in _uniqueness_storage_runtime:
    _uniqueness_storage_runtime[inspector] = set()
  if inspector not in _uniqueness_storage_disk:
    _uniqueness_storage_disk[inspector] = {}
    data_dir = utils.data_dir()
    inspector_path = os.path.join(data_dir, inspector)
    if os.path.isdir(inspector_path):
      for year_folder in os.listdir(inspector_path):
        year_disk = int(year_folder)
        year_path = os.path.join(inspector_path, year_folder)
        if os.path.isdir(year_path):
          for report_id_disk in os.listdir(year_path):
            report_path = os.path.join(year_path, report_id_disk)
            if os.path.isdir(report_path):
              if report_id_disk in _uniqueness_storage_disk[inspector]:
                msg = "[%s] Duplicate report_id: %s is saved under %d and %d" %\
                        (inspector,
                        report_id_disk,
                        _uniqueness_storage_disk[inspector][report_id_disk],
                        year_disk)
                print(msg)
                admin.log_duplicate_id(scraper, report_id_disk, msg)
              _uniqueness_storage_disk[inspector][report_id_disk] = year_disk

  if report_id in _uniqueness_storage_runtime[inspector]:
    msg = "[%s] Duplicate report_id: %s has been used twice this session" % \
            (inspector, report_id)
    print(msg)
    admin.log_duplicate_id(scraper, report_id, msg)
  elif report_id in _uniqueness_storage_disk[inspector]:
    if report_year != _uniqueness_storage_disk[inspector][report_id]:
      msg = "[%s] Duplicate report_id: %s is saved under %d and %d" % \
              (inspector,
              report_id,
              _uniqueness_storage_disk[inspector][report_id],
              report_year)
      print(msg)
      admin.log_duplicate_id(scraper, report_id, msg)
  _uniqueness_storage_runtime[inspector].add(report_id)


# run over common string fields automatically
sanitize_table = str.maketrans({
  "\xa0": " ",          # no-break space
  "\u200b": " ",        # zero-width space
  "\u2013": "-",        # en dash
  "\u2014": "-",        # em dash
  "\u2018": "'",        # left single quotation mark
  "\u2019": "'",        # right single quotation mark
  "\u201c": "\"",       # left double quotation mark
  "\u201d": "\"",       # right double quotation mark
})
def sanitize(string):
  return string.translate(sanitize_table).strip()

# invalid to use in a report ID
def invalid_chars():
  return ('/', '\\', ':', '*', '?', '"', '<', '>', '|', '\r', '\n')

# a scraper can use this to slugify a report_id
def slugify(report_id):
  copy = report_id
  for char in invalid_chars():
    copy = copy.replace(char, "-")
  return copy

def download_report(report):
  report_path = path_for(report, report['file_type'])
  binary = (report['file_type'].lower() in ('pdf', 'doc', 'ppt', 'docx', 'xls'))

  result = utils.download(
    report['url'],
    os.path.join(utils.data_dir(), report_path),
    {'binary': binary}
  )
  if result:
    return report_path
  else:
    return None

FILE_EXTENSIONS_HTML = ("htm", "html", "shtml", "cfm", "php", "asp", "aspx")

def extract_metadata(report):
  report_path = path_for(report, report['file_type'])

  file_type_lower = report['file_type'].lower()
  if file_type_lower == "pdf":
    metadata = utils.metadata_from_pdf(report_path)
    if metadata:
      report['pdf'] = metadata
      return metadata
  elif file_type_lower == "doc":
    metadata = utils.metadata_from_doc(report_path)
    if metadata:
      report['doc'] = metadata
      return metadata
  elif file_type_lower == "docx":
    metadata = utils.metadata_from_docx(report_path)
    if metadata:
      report['docx'] = metadata
      return metadata
  elif file_type_lower in FILE_EXTENSIONS_HTML:
    return None
  else:
    logging.warn("Unknown file type, don't know how to extract metadata!")
    return None

# relies on putting text next to report_path
def extract_report(report):
  report_path = path_for(report, report['file_type'])
  real_report_path = os.path.abspath(os.path.expandvars(os.path.join(utils.data_dir(), report_path)))

  text_path = "%s.txt" % os.path.splitext(report_path)[0]
  real_text_path = os.path.abspath(os.path.expandvars(os.path.join(utils.data_dir(), text_path)))

  if os.path.exists(real_text_path):
    # This report has already had its text extracted
    return text_path

  file_type_lower = report['file_type'].lower()
  if file_type_lower == "pdf":
    utils.text_from_pdf(real_report_path, real_text_path)
    return text_path
  elif file_type_lower == "doc":
    utils.text_from_doc(real_report_path, real_text_path)
    return text_path
  elif file_type_lower == "docx":
    utils.text_from_docx(real_report_path, real_text_path)
    return text_path
  elif file_type_lower in FILE_EXTENSIONS_HTML:
    utils.text_from_html(real_report_path, real_text_path)
    return text_path
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

# get year for a report from its publish date
def year_from(report):
  return int(report['published_on'].split("-")[0])

# assume standard options for IG scrapers, since/year
def year_range(options, archive):
  this_year = datetime.datetime.now().year

  # --archive will use scraper's oldest year, if passed in.
  if archive and options.get('archive'):
    since = archive

  # otherwise, use --since year if present
  else:
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
  elif datetime.datetime.now().month == 1:
    # During January, default to crawling for the current year and last year.
    # This overlap ensures more reports are caught as they are posted, and
    # cuts down on spurious "no reports found" errors.
    year_range = list(range(this_year - 1, this_year + 1))
  else:
    year_range = list(range(this_year, this_year + 1))

  return year_range

class NoReportsFoundError(AssertionError):
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return "No reports were found for %s" % self.value
