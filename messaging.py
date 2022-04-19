#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

from base64 import b64encode
from pathlib import Path
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, Disposition, FileContent, FileName, FileType
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
    api_key = EMAIL_DATA['apiKey']
    to_addresses = EMAIL_DATA['to']

    if None in [to_addresses, from_address, api_key]:
        print('Required variables for sending emails are missing. No emails sent.')

        return None

    return _send_email_with_sendgrid(from_address, api_key, to_addresses, subject, body, [attachment])

def _send_email_with_sendgrid(from_address, api_key, to_address, subject, body, attachments=None):
    '''
    email_server: dict
    to_address: string | string[]
    subject: string
    body: string | MIMEMultipart
    attachments: string[] - paths to text files to attach to the email
    Send an email.
    '''
    if attachments is None:
        attachments=[]

    message = Mail(
        from_email=from_address,
        to_emails=to_address,
        subject=subject,
        html_content=body)

    for location in attachments:
        path = Path(location)

        if not path.exists():
            continue

        content = b64encode(path.read_bytes()).decode()

        message.attachment = Attachment(
            FileContent(content), FileName(f'{path.name}.csv'), FileType('text/csv'), Disposition('attachment')
        )

    try:
        client = SendGridAPIClient(api_key)

        return client.send(message)
    except Exception as error:
        print(f'Error sending email with SendGrid: {error}')

        return error
