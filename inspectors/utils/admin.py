# functions for communicating with an admin

import os
import sys
import traceback
import yaml
import logging

import smtplib
import email.utils
from email.mime.text import MIMEText

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
