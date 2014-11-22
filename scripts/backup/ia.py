###############################################################################
#
# This script controls the backup process to the Internet Archive.
#
# It's meant to be operated by Eric Mill, who as of 2014 manages the project
# and its collection on the Internet Archive.
#
# If you'd like to upload IG reports with your own IA account, please contact
# Eric first at eric@konklone.com to coordinate.
#
###############################################################################

import internetarchive
import os, sys, traceback
import json, logging, requests

# The unique collection ID, assigned by Internet Archive staff.
COLLECTION_NAME = "usinspectorsgeneral"

# The special item ID for the bulk download file, chosen by Eric.
BULK_ITEM_NAME = "us-inspectors-general.bulk"



# given an IG report, a year, and its report_id:
# create an item in the Internet Archive
def backup_report(ig, year, report_id, options=None):
  if options is None: options = {}

  logging.warn("")

  # this had better be there
  report = json.load(open(metadata_path(ig, year, report_id)))
  if report.get('unreleased'):
    logging.warn("[%s][%s][%s] Unreleased report, skipping." % (ig, year, report_id))
    return True

  if already_uploaded(ig, year, report_id) and (options.get("force") is not True):
    logging.warn("[%s][%s][%s] Already backed up, skipping." % (ig, year, report_id))
    return True

  logging.warn("[%s][%s][%s] Initializing item." % (ig, year, report_id))
  item_id = item_id_for(ig, year, report_id)
  item = internetarchive.get_item(item_id)

  if item.exists and (options.get("force") is not True):
    logging.warn("[%s][%s][%s] Ooooops, item does exist. Marking as done, and stopping." % (ig, year, report_id))
    mark_as_uploaded(ig, year, report_id)
    return True

  metadata = collection_metadata()
  metadata.update(item_metadata(report))

  # 1) add the metadata file, and attach the IA item metadata to it
  logging.warn("[%s][%s][%s] Sending metadata!" % (ig, year, report_id))
  success = upload_files(item,
    metadata_path(ig, year, report_id),
    metadata,
    options
  )

  if not success:
    logging.warn("[%s][%s][%s] :( Error sending metadata." % (ig, year, report_id))
    return False

  # 2) Unless --meta is on, upload the associated report files.
  if not options.get("meta"):
    report_path = file_path(ig, year, report_id, report['file_type'])
    text_path = file_path(ig, year, report_id, "txt")

    to_upload = []
    if os.path.exists(report_path):
      to_upload.append(report_path)
    if (report_path != text_path) and os.path.exists(text_path):
      to_upload.append(text_path)

    if len(to_upload) > 0:
      logging.warn("[%s][%s][%s] Sending %i report files!" % (ig, year, report_id, len(to_upload)))
      success = upload_files(item, to_upload, None, options)

    if not success:
      logging.warn("[%s][%s][%s] :( Error uploading report itself." % (ig, year, report_id))
      return False

  logging.warn("[%s][%s][%s] :) Uploaded:\n%s" % (ig, year, report_id, ia_url_for(item_id)))
  mark_as_uploaded(ig, year, report_id)

  return True

# one-off: back up a given file, known to be the bulk accompaniment
def backup_bulk(bulk_path, options):
  if not os.path.exists(bulk_path):
    logging.warn("Bulk file doesn't exist! Stopping.")
    return False

  logging.warn("Initializing bulk item.")
  item_id = BULK_ITEM_NAME
  item = internetarchive.get_item(item_id)

  metadata = collection_metadata()
  metadata.update(bulk_metadata())

  logging.warn("Sending bulk metadata and file!")
  success = upload_files(item,
    bulk_path,
    metadata,
    options
  )

  if not success:
    logging.warn(":( Error uploading bulk file.")
    return False

  logging.warn(":) Uploaded bulk file successfully.")
  return True

# metadata that will be applied to ALL items
# TODO: move some of this out to admin.yml?
def collection_metadata():
  data = {
    # TODO: collection identifier, once granted
    # 'collection': 'us-inspectors-general',
    'mediatype': 'texts', # best I got
    'contributor': 'github.com/unitedstates',
    'creator': 'United States Government',
    'adder': 'eric@konklone.com',
    'uploader': 'eric@konklone.com',
    'language': 'english',

    # custom metadata
    'project': 'https://github.com/unitedstates/inspectors-general',
    'contact-email': 'eric@konklone.com',
    'contact-twitter': '@konklone'
  }

  data['subject'] = ";".join([
    "inspector general", "us government", "government oversight"
  ]) # less is more

  data['notes'] = """
As a work of the United States government, this work is in the public domain inside the United States.
  """

  return data

# metadata specific to the item
# required fields on all IG reports:
#    published_on, report_id, title, inspector, inspector_url,
#    agency, agency_name
def item_metadata(report):
  data = {
    'title': report['title'],
    'date': report['published_on']
  }

  data['description'] = """
A report by an inspector general in the United States federal government.
Gathered by web scrapers written and maintained by a team of volunteers.
Submitted to the Internet Archive by Eric Mill.
  """

  data['publisher'] = report['inspector_url']
  data['report-id'] = report['report_id']
  data['report-inspector'] = report['inspector']
  data['report-year'] = str(report['year'])

  if report.get('url'):
    data['original-url'] = report['url']

  if report.get('type'):
    data['report-type'] = report['type']

  return data

def bulk_metadata():
  data = {}

  data['title'] = "Bulk Download of US Inspector General reports"
  data['description'] = """
Bulk download of US federal government inspector general reports.
Gathered by web scrapers written and maintained by a team of volunteers.
Submitted to the Internet Archive by Eric Mill.
"""

  data['publisher'] = "https://github.com/unitedstates/inspectors-general"

  return data

# actually send the report file up to the IA, with attached metadata
def upload_files(item, paths, metadata, options):

  # for the bulk upload (a giant .zip), don't use the IA's derivation queue
  if options.get("bulk"):
    queue_derive = False
  # for normal reports, definitely derive stuff, to get the sweet viewer
  else:
    queue_derive = True

  try:
    return item.upload(paths,
      metadata=metadata,
      access_key=options['config']['access_key'],
      secret_key=options['config']['secret_key'],
      debug=options.get("dry_run", False),

      verbose=True, # I love output
      # queue_derive=False, # don't put it into IA's derivation queue
      ignore_preexisting_bucket=True, # always overwrite

      retries=3, # it'd be nicer to look up the actual rate limit
      retries_sleep=2
    )
  except requests.exceptions.HTTPError as exc:
    format_exception(exc)
    return False

def file_path(ig, year, report_id, file_type):
  return "data/%s/%s/%s/report.%s" % (ig, year, report_id, file_type)

def metadata_path(ig, year, report_id):
  return "data/%s/%s/%s/report.json" % (ig, year, report_id)

def marker_path(ig, year, report_id):
  return "data/%s/%s/%s/ia.done" % (ig, year, report_id)

def already_uploaded(ig, year, report_id):
  return os.path.exists(marker_path(ig, year, report_id))

def mark_as_uploaded(ig, year, report_id):
  open(marker_path(ig, year, report_id), "w").close()

def ia_url_for(item_id):
  return "https://archive.org/details/%s" % item_id

def item_id_for(ig, year, report_id):
  return "%s.%s-%s-%s" % (COLLECTION_NAME, ig, year, report_id)

def format_exception(exception):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
