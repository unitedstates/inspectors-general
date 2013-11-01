import utils, os

# Save a report to disk, provide output along the way.
#
# 1) download report to disk
# 2) extract text from downloaded report using report['file_type']
# 3) write report metadata to disk
#
# fields used: file_type, url, inspector, year, slug
# fields added: report_path, text_path

def save_report(report):
  print "[%s][%s]" % (report['type'], report['published_on'])

  report['report_path'] = download_report(report)
  print "\treport: %s" % report['report_path']

  report['text_path'] = extract_report(report)
  print "\ttext: %s" % report['text_path']

  data_path = write_report(report)
  print "\tdata: %s" % data_path

def download_report(report):
  report_path = "%s/%s/%s/report.%s" % (report['inspector'], report['year'], report['slug'], report['file_type'])
  binary = (report['file_type'] == 'pdf')

  utils.download(
    report['url'],
    "%s/%s" % (utils.data_dir(), report_path),
    {'binary': binary}
  )
  return report_path

# relies on putting text next to report_path
def extract_report(report):
  return utils.extract_text(report['report_path'])

def write_report(report):
  data_path = "%s/%s/%s/data.json" % (report['inspector'], report['year'], report['slug'])
  utils.write(
    utils.json_for(report),
    "%s/%s" % (utils.data_dir(), data_path)
  )
  return data_path

def cache(inspector, path):
  return os.path.join(utils.cache_dir(), inspector, path)