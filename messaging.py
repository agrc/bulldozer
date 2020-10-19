#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename, isfile
from smtplib import SMTP

from servers import EMAIL_DATA


def send_email(subject, body, attachment=''):
    '''
    to: string | string[]
    subject: string
    body: string | MIMEMultipart
    attachment: string - the path to a text file to attach.

    Send an email.
    '''
    from_address = EMAIL_DATA['from']
    smtp_server = EMAIL_DATA['server']
    smtp_port = EMAIL_DATA['port']
    to_addresses = EMAIL_DATA['to']

    if None in [to_addresses, from_address, smtp_server, smtp_port]:
        print('Required variables for sending emails are missing. No emails sent.')

        return None

    message = MIMEMultipart()
    if isinstance(body, str):
        message.attach(MIMEText(body, 'html'))
    else:
        message = body

    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = COMMASPACE.join(to_addresses)
    message['Date'] = formatdate(localtime=True)

    if isfile(attachment):
        with (open(attachment, 'r', encoding='utf-8')) as log_file:
            log_file_attachment = MIMEText(log_file.read(), 'csv')

        log_file_attachment.add_header('Content-Disposition', 'attachment; filename="{}"'.format(basename(attachment)))
        message.attach(log_file_attachment)

    smtp = SMTP(smtp_server, smtp_port)
    smtp.sendmail(from_address, to_addresses, message.as_string())
    smtp.quit()

    return smtp
