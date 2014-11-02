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
import os, json, logging

# given an IG report, a year, and its report_id:
# create an item in the Internet Archive
def backup_report(ig, year, report_id, options=None):
  if options is None: options = {}

  logging.warn("")

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

  # this had better be there
  report = json.load(open(metadata_path(ig, year, report_id)))

  metadata = collection_metadata()
  metadata.update(item_metadata(report))

  # first, add the metadata file, and attach the IA item metadata to it
  logging.warn("[%s][%s][%s] Sending metadata!" % (ig, year, report_id))
  success = upload_file(item,
    metadata_path(ig, year, report_id),
    metadata,
    options
  )

  if not success:
    logging.warn("[%s][%s][%s] :( Error sending metadata." % (ig, year, report_id))
    return False

  logging.warn("[%s][%s][%s] :) Uploaded:\n\t%s" % (ig, year, report_id, ia_url_for(item_id)))
  mark_as_uploaded(ig, year, report_id)

  return True


def item_id_for(ig, year, report_id):
  return "us-inspectors-general.%s-%s-%s" % (ig, year, report_id)


# metadata that will be applied to ALL items
# TODO: move some of this out to admin.yml?
def collection_metadata():
  return {
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

  data['subject'] = ";".join([
    "inspector general", "us government", "government oversight"
  ]) # less is more

  data['notes'] = """
As a work of the United States government, this work is in the public domain inside the United States.
  """

  data['publisher'] = report['inspector_url']
  data['report-id'] = report['report_id']
  data['report-year'] = str(report['year'])

  if report.get('url'):
    data['original-url'] = report['url']

  if report.get('type'):
    data['report-type'] = report['type']

  return data

# actually send the report file up to the IA, with attached metadata
def upload_file(item, path, metadata, options):
  return item.upload(path,
    metadata=metadata,
    access_key=options['config']['access_key'],
    secret_key=options['config']['secret_key'],
    debug=options.get("dry_run", False),

    verbose=True, # I love output
    queue_derive=False, # don't put it into IA's derivation queue
    ignore_preexisting_bucket=True, # always overwrite

    retries=3, # it'd be nicer to look up the actual rate limit
    retries_sleep=2
  )

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