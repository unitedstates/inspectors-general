import utils, os
import logging

# Save a report to disk, provide output along the way.
#
# 1) download report to disk
# 2) extract text from downloaded report using report['file_type']
# 3) write report metadata to disk
#
# fields used: file_type, url, inspector, year, report_id
# fields added: report_path, text_path

def save_report(report):
  logging.warn("[%s][%s][%s]" % (report['type'], report['published_on'], report['report_id']))

  report_path = download_report(report)
  logging.warn("\treport: %s" % report_path)

  text_path = extract_report(report)
  logging.warn("\ttext: %s" % text_path)

  data_path = write_report(report)
  logging.warn("\tdata: %s" % data_path)

def download_report(report):
  report_path = path_for(report, report['file_type'])
  binary = (report['file_type'] == 'pdf')

  utils.download(
    report['url'],
    "%s/%s" % (utils.data_dir(), report_path),
    {'binary': binary}
  )
  return report_path

# relies on putting text next to report_path
def extract_report(report):
  report_path = path_for(report, report['file_type'])

  if report['file_type'] == "pdf":
    return utils.text_from_pdf(report_path)
  elif report['file_type'] == "html":
    logging.warn("\tTODO: extract text from HTML.")
    return None
  else:
    logging.warn("Unknown file type, don't know how to extract text!")
    return None

def write_report(report):
  data_path = path_for(report, "json")

  utils.write(
    utils.json_for(report),
    "%s/%s" % (utils.data_dir(), data_path)
  )
  return data_path


def path_for(report, ext):
  return "%s/%s/%s/report.%s" % (report['inspector'], report['year'], report['report_id'], ext)

def cache(inspector, path):
  return os.path.join(utils.cache_dir(), inspector, path)