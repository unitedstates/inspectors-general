# functions for communicating with an admin

import os
import sys
import traceback
import yaml
import logging
import re

import smtplib
import email.utils
from email.mime.text import MIMEText

import json
import urllib.request
import urllib.parse

# read in an opt-in config file for changing directories and supplying email settings
# returns None if it's not there, and this should always be handled gracefully
path = "admin.yml"
if os.path.exists(path):
    config = yaml.load(open(path))
else:
    config = None


def notify(body):
    try:
        if isinstance(body, Exception):
            body = format_exception(body)

        logging.error(body)  # always print it

        if config:
            details = config.get('email')
            if details:
                send_email(body)

            if config.get('slack'):
                send_slack(body)

    except Exception as exception:
        print("Exception logging message to admin, halting as to avoid loop")
        print(format_exception(exception))


def format_exception(exception):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

# this should only be called if the settings are definitely there


def send_email(message):
    settings = config['email']

    # adapted from http://www.doughellmann.com/PyMOTW/smtplib/
    msg = MIMEText(message)
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

def copy_if_present(key, src, dst):
    if key in src:
        dst[key] = src[key]

INSPECTOR_RE = re.compile('''File "\\.?inspectors(?:/|\\\\)([a-z]+)\\.py", line ([0-9]+), in ([^\n]+)\n''')
HTTP_ERROR_RE = re.compile('''scrapelib\\.HTTPError: ([0-9]+) while retrieving ([^\n]+)\n''')

def send_slack(body):
    options = config["slack"]
    webhook_url = options["webhook"]

    body = str(body)
    lines = body.split('\n')

    # Scan up to the point where the traceback starts
    index = 0
    while index < len(lines) and lines[index] != "Traceback (most recent call last):":
        index = index + 1
    # Skip the traceback
    index = index + 1
    # Scan until the first non-indented line, after the traceback
    while index < len(lines) and (lines[index] == "" or lines[index][0] == " "):
        index = index + 1
    # If we ran off the end of the message because it's in an unexpected
    # format, just use the whole thing
    if index == len(lines):
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
        pretext = "%s error while downloading %s" % \
                  (http_error_match.group(1), http_error_match.group(2))
        message = {
            "attachments": [
                {
                    "fallback": fallback,
                    "text": body,
                    "color": "warning",
                    "pretext": pretext
                }
            ]
        }
    elif class_name and scraper and line_num and function:
        pretext = ("%s was thrown while running %s.py " + \
                  "(line %s, in function %s)") % \
                  (class_name, scraper, line_num, function)
        message = {
            "attachments": [
                {
                    "fallback": fallback,
                    "text": body,
                    "color": "danger",
                    "pretext": pretext
                }
            ]
        }
    else:
        message = {
            "text": str(body)
        }

    copy_if_present("username", options, message)
    copy_if_present("icon_url", options, message)
    copy_if_present("icon_emoji", options, message)
    copy_if_present("channel", options, message)

    message_json = json.dumps(message)
    message_bytes = message_json.encode('utf-8')

    request = urllib.request.Request(webhook_url, message_bytes)
    request.add_header('Content-Type', 'application/json; charset=utf-8')
    urllib.request.urlopen(request)
