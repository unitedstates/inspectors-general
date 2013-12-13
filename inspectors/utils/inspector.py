import utils, os

# Save a report to disk, provide output along the way.
#
# 1) download report to disk
# 2) extract text from downloaded report using report['file_type']
# 3) write report metadata to disk
#
# fields used: file_type, url, inspector, year, report_id
# fields added: report_path, text_path

def save_report(report):
  print "[%s][%s][%s]" % (report['type'], report['published_on'], report['report_id'])

  report_path = download_report(report)
  print "\treport: %s" % report_path

  text_path = extract_report(report_path)
  print "\ttext: %s" % text_path

  data_path = write_report(report)
  print "\tdata: %s" % data_path

def download_report(report):
  report_path = "%s/%s/%s/report.%s" % (report['inspector'], report['year'], report['report_id'], report['file_type'])
  binary = (report['file_type'] == 'pdf')

  utils.download(
    report['url'],
    "%s/%s" % (utils.data_dir(), report_path),
    {'binary': binary}
  )
  return report_path

# relies on putting text next to report_path
def extract_report(report_path):
  return utils.extract_text(report_path)

def write_report(report):
  data_path = "%s/%s/%s/report.json" % (report['inspector'], report['year'], report['report_id'])
  utils.write(
    utils.json_for(report),
    "%s/%s" % (utils.data_dir(), data_path)
  )
  return data_path

def cache(inspector, path):
  return os.path.join(utils.cache_dir(), inspector, path)