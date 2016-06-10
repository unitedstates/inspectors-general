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


def notify(body):
  for error_handler in error_handlers:
    try:
      if isinstance(body, Exception):
        body = format_exception(body)
      error_handler.log(body)
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


def format_exception(exception):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))


def copy_if_present(key, src, dst):
  if key in src:
    dst[key] = src[key]

INSPECTOR_RE = re.compile('''File "\\.?inspectors(?:/|\\\\)([a-z]+)\\.py", line ([0-9]+), in ([^\n]+)\n''')
HTTP_ERROR_RE = re.compile('''scrapelib\\.HTTPError: ([0-9]+) while retrieving ([^\n]+)\n''')
TRACEBACK_STR = "Traceback (most recent call last):"

class ErrorHandler(object):
  def log(self, body):
    if not self.options:
      return
    lines = body.split('\n')

    # Scan up to the point where the traceback starts
    index = 0
    while index < len(lines) and lines[index].find(TRACEBACK_STR) != -1:
      index = index + 1
    # Skip the traceback
    index = index + 1
    # Scan until the first non-indented line, after the traceback
    while index < len(lines) and (lines[index] == "" or lines[index][0] == " "):
      index = index + 1
    # If we ran off the end of the message because it's in an unexpected
    # format, just use the whole thing
    if index >= len(lines):
      index = 0
    # Take the remaining text as the exception message
    exception_message = '\n'.join(lines[index:])
    # Use one line only of the exception message as a fallback message for
    # text-only clients
    fallback = lines[index]

    # The exception type should be the first thing after the traceback,
    # followed by a colon
    if exception_message.find(':') != -1:
      class_name = exception_message[:exception_message.find(':')]
    else:
      class_name = None

    scraper = None
    line_num = None
    function = None
    scraper_matches = INSPECTOR_RE.findall(body)
    if scraper_matches:
      scraper = scraper_matches[-1][0]
      line_num = scraper_matches[-1][1]
      function = scraper_matches[-1][2]

    http_error_match = HTTP_ERROR_RE.search(body)
    if http_error_match:
      self.log_http_error(http_error_match.group(1), http_error_match.group(2),
                          fallback, body)
    elif class_name and scraper and line_num and function:
      self.log_exception(class_name, scraper, line_num, function,
                         fallback, body)
    elif body.startswith("QA results for"):
      self.log_qa("\n".join(lines[1:]), fallback)
    else:
      self.log_fallback(str(body))

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

  def log_http_error(self, http_status_code, url, fallback, body):
    pretext = "%s error while downloading %s" % (http_status_code, url)
    self.send_message({
      "attachments": [
        {
          "fallback": fallback,
          "text": body,
          "color": "warning",
          "pretext": pretext
        }
      ]
    })

  def log_exception(self, class_name, scraper, line_num, function,
                    fallback, body):
    pretext = ("%s was thrown while running %s.py (line %s, in function %s)" %
               (class_name, scraper, line_num, function))
    self.send_message({
      "attachments": [
        {
          "fallback": fallback,
          "text": body,
          "color": "danger",
          "pretext": pretext
        }
      ]
    })

  def log_qa(self, text, fallback):
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

  def log_fallback(self, body):
    self.send_message({
      "text": str(body)
    })


class DashboardErrorHandler(ErrorHandler):
  def __init__(self):
    self.options = config.get("dashboard")
    self.dashboard_data = {}
    atexit.register(self.dashboard_send)

  def log_http_error(self, http_status_code, url, fallback, body):
    pass  # self.dashboard_data[todo]

  def log_duplicate_id(self, scraper, report_id, msg):
    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "duplicate_ids" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["duplicate_ids"] = []
    self.dashboard_data[scraper]["duplicate_ids"].append(report_id)

  def log_exception(self, class_name, scraper, line_num, function,
                    fallback, body):
    if scraper not in self.dashboard_data:
      self.dashboard_data[scraper] = {}
    if "exceptions" not in self.dashboard_data[scraper]:
      self.dashboard_data[scraper]["exceptions"] = []
    entry = {
      "class_name": class_name,
      "filename": "inspectors/%s.py" % scraper,
      "line_num": line_num,
      "function": function,
      "traceback": body
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

  def log_qa(self, text, fallback):
    pass

  def log_fallback(self, body):
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
      else:
        severity = 0
      self.dashboard_data[scraper]["severity"] = severity

      if "duplicate_ids" in self.dashboard_data[scraper]:
        self.dashboard_data[scraper]["duplicate_ids"].sort()

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
