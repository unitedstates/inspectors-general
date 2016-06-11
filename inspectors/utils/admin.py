# functions for communicating with an admin

import os
import sys
import traceback
import yaml
import logging
import re
import atexit

import smtplib
import email.utils
from email.mime.text import MIMEText

import json
import urllib.request
import urllib.parse

# read in an opt-in config file for changing directories and supplying settings
# returns None if it's not there, and this should always be handled gracefully
path = "admin.yml"
if os.path.exists(path):
  config = yaml.load(open(path))
else:
  config = None


def log_exception(e):
  for error_handler in error_handlers:
    try:
      error_handler.log_exception(e)
    except Exception as exception:
      print("Exception logging message to admin, halting as to avoid loop")
      print(format_exception(exception))


def log_duplicate_id(scraper, report_id, msg):
  for error_handler in error_handlers:
    try:
      error_handler.log_duplicate_id(scraper, report_id, msg)
    except Exception as exception:
      print("Exception logging message to admin, halting as to avoid loop")
      print(format_exception(exception))


def log_no_date(scraper, report_id, title, url=None):
  for error_handler in error_handlers:
    try:
      error_handler.log_no_date(scraper, report_id, title, url)
    except Exception as exception:
      print("Exception logging message to admin, halting as to avoid loop")
      print(format_exception(exception))


def log_report(scraper):
  for error_handler in error_handlers:
    try:
      error_handler.log_report(scraper)
    except Exception as exception:
      print(format_exception(exception))


def log_qa(report_text):
  for error_handler in error_handlers:
    try:
      error_handler.log_qa(report_text)
    except Exception as exception:
      print(format_exception(exception))


def log_http_error(e, url, scraper=None):
  for error_handler in error_handlers:
    try:
      error_handler.log_http_error(e, url, scraper)
    except Exception as exception:
      print(format_exception(exception))


def format_exception(exception):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))


def parse_scraper_traceback():
  exc_traceback = sys.exc_info()[2]
  for filename, line_number, function_name, text in traceback.extract_tb(exc_traceback):
    inspector_match = INSPECTOR_RE.match(filename)
    if inspector_match:
      return inspector_match.group(1), line_number, function_name
  return None, None, None


def copy_if_present(key, src, dst):
  if key in src:
    dst[key] = src[key]

INSPECTOR_RE = re.compile("^inspectors(?:/|\\\\)([a-z]+)\\.py$")
HTTP_ERROR_RE = re.compile('''scrapelib\\.HTTPError: ([0-9]+) while retrieving ([^\n]+)\n''')
TRACEBACK_STR = "Traceback (most recent call last):"

class ErrorHandler(object):
  def log_report(self, scraper):
    pass

  def log_no_date(self, scraper, report_id, title, url):
    if url is None:
      message = ("[%s] No date was found for %s, \"%s\""
                 % (scraper, report_id, title))
    else:
      message = ("[%s] No date was found for %s, \"%s\" (%s)"
                 % (scraper, report_id, title, url.replace(" ", "%20")))
    self.log(message)

  def log_exception(self, exception):
    self.log(format_exception(exception))


class ConsoleErrorHandler(ErrorHandler):
  def __init__(self):
    self.uniqueness_messages = []
    atexit.register(self.print_duplicate_messages)

  def log_duplicate_id(self, scraper, report_id, msg):
    self.uniqueness_messages.append(msg)

  def print_duplicate_messages(self):
    self.log("\n".join(self.uniqueness_messages))

  def log(self, body):
    logging.error(body)

  def log_http_error(self, exception, url, scraper):
    # intentionally print instead of using logging,
    # so that all 404s get printed at the end of the log
    print("Error downloading %s:\n\n%s" % (url, format_exception(exception)))

  def log_qa(self, text):
    self.log(text)


class EmailErrorHandler(ErrorHandler):
  def __init__(self):
    self.uniqueness_messages = []
    atexit.register(self.print_duplicate_messages)

  def log_duplicate_id(self, scraper, report_id, msg):
    self.uniqueness_messages.append(msg)

  def print_duplicate_messages(self):
    self.log("\n".join(self.uniqueness_messages))

  def log(self, body):
    settings = config['email']

    # adapted from http://www.doughellmann.com/PyMOTW/smtplib/
    msg = MIMEText(body)
    msg.set_unixfrom('author')
    msg['To'] = email.utils.formataddr(('Recipient', settings['to']))
    msg['From'] = email.utils.formataddr((settings['from_name'], settings['from']))
    msg['Subject'] = settings['subject']

    server = smtplib.SMTP(settings['hostname'])
    try:
      server.ehlo()
      if settings['starttls'] and server.has_extn('STARTTLS'):
        server.starttls()
        server.ehlo()

      server.login(settings['user_name'], settings['password'])
      server.sendmail(settings['from'], [settings['to']], msg.as_string())
    finally:
      server.quit()

    logging.info("Sent email to %s" % settings['to'])

  def log_http_error(self, exception, url, scraper):
    pass

  def log_qa(self, text):
    pass


class SlackErrorHandler(ErrorHandler):
  def __init__(self):
    self.options = config.get("slack")
    self.uniqueness_messages = []
    atexit.register(self.print_duplicate_messages)

  def log_duplicate_id(self, scraper, report_id, msg):
    self.uniqueness_messages.append(msg)

  def print_duplicate_messages(self):
    if self.uniqueness_messages:
      self.send_message({
        "text": "\n".join(self.uniqueness_messages)
      })

  def send_message(self, message):
    copy_if_present("username", self.options, message)
    copy_if_present("icon_url", self.options, message)
    copy_if_present("icon_emoji", self.options, message)
    copy_if_present("channel", self.options, message)

    message_json = json.dumps(message)
    message_bytes = message_json.encode("utf-8")

    request = urllib.request.Request(self.options["webhook"], message_bytes)
    request.add_header("Content-Type", "application/json; charset=utf-8")
    urllib.request.urlopen(request)

  def log_http_error(self, exception, url, scraper):
    http_status_code = exception.response.status_code
    body = format_exception(exception)

    pretext = ("[%s] %s error while downloading %s" %
               (scraper, http_status_code, url))
    self.send_message({
      "attachments": [
        {
          "fallback": pretext,
          "text": body,
          "color": "warning",
          "pretext": pretext
        }
      ]
    })

  def log_exception(self, exception):
    class_name = "%s.%s" % (exception.__module__, exception.__class__.__name__)
    scraper, line_num, function = parse_scraper_traceback()
    fallback = "%s.%s: %s" % (exception.__module__,
                              exception.__class__.__name__,
                              exception)

    pretext = ("%s was thrown while running %s.py (line %s, in function %s)" %
               (class_name, scraper, line_num, function))
    self.send_message({
      "attachments": [
        {
          "fallback": fallback,
          "text": format_exception(exception),
          "color": "danger",
          "pretext": pretext
        }
      ]
    })

  def log_qa(self, text):
    fallback = text.split("\n", 1)[0]
    self.send_message({
      "attachments": [
        {
          "fallback": fallback,
          "text": text,
          "color": "danger",
          "pretext": fallback
        }
      ]
    })

  def log_no_date(self, scraper, report_id, title, url):
    if url is None:
      message = ("[%s] No date was found for %s, \"%s\""
                 % (scraper, report_id, title))
    else:
      message = ("[%s] No date was found for %s, \"%s\" (%s)"
                 % (scraper, report_id, title, url.replace(" ", "%20")))
    self.send_message({
      "attachments": [
        {
          "fallback": message,
          "text": message,
          "color": "warning"
        }
      ]
    })


class DashboardErrorHandler(ErrorHandler):
  def __init__(self):
    self.options = config.get("dashboard")
    self.dashboard_data = {}
    atexit.register(self.dashboard_send)

  def log_http_error(self, exception, url, scraper):
    if scraper is None:
      return
    http_status_code = exception.response.status_code

    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "http_errors" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["http_errors"] = []
    entry = {
      "status_code": http_status_code,
      "url": url
    }
    self.dashboard_data[scraper]["http_errors"].append(entry)

  def log_duplicate_id(self, scraper, report_id, msg):
    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "duplicate_ids" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["duplicate_ids"] = []
    self.dashboard_data[scraper]["duplicate_ids"].append(report_id)

  def log_exception(self, exception):
    class_name = "%s.%s" % (exception.__module__, exception.__class__.__name__)
    scraper, line_num, function = parse_scraper_traceback()

    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "exceptions" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["exceptions"] = []
    entry = {
      "class_name": class_name,
      "filename": "inspectors/%s.py" % scraper,
      "line_num": line_num,
      "function": function,
      "traceback": format_exception(exception)
    }
    self.dashboard_data[scraper]["exceptions"].append(entry)

  def log_no_date(self, scraper, report_id, title, url):
    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "missing_dates" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["missing_dates"] = []
    entry = {
      "report_id": report_id,
      "title": title,
      "url": url
    }
    self.dashboard_data[scraper]["missing_dates"].append(entry)

  def log_qa(self, text):
    pass

  def dashboard_send(self):
    if not self.dashboard_data:
      return

    for scraper in self.dashboard_data:
      if "exceptions" in self.dashboard_data[scraper]:
        severity = 2
      elif "duplicate_ids" in self.dashboard_data[scraper]:
        severity = 1
      elif "missing_dates" in self.dashboard_data[scraper]:
        severity = 1
      elif "http_errors" in self.dashboard_data[scraper]:
        severity = 1
      else:
        severity = 0
      self.dashboard_data[scraper]["severity"] = severity

      if "duplicate_ids" in self.dashboard_data[scraper]:
        self.dashboard_data[scraper]["duplicate_ids"].sort()
      if "report_count" not in self.dashboard_data[scraper]:
        self.dashboard_data[scraper]["report_count"] = 0

    options = config["dashboard"]
    message_json = json.dumps(self.dashboard_data)
    message_bytes = message_json.encode("utf-8")
    url = options["url"] + "?secret=" + urllib.parse.quote(options["secret"])
    request = urllib.request.Request(url, message_bytes)
    request.add_header("Content-Type", "application/json; charset=utf-8")
    request.get_method = lambda: "PUT"
    urllib.request.urlopen(request)

  def log_report(self, scraper):
    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "report_count" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["report_count"] = 1
    else:
      self.dashboard_data[scraper]["report_count"] = (1 +
          self.dashboard_data[scraper]["report_count"])


error_handlers = [ConsoleErrorHandler()]
if config:
  if config.get("email"):
    error_handlers.append(EmailErrorHandler())
  if config.get("slack"):
    error_handlers.append(SlackErrorHandler())
  if config.get("dashboard"):
    error_handlers.append(DashboardErrorHandler())
