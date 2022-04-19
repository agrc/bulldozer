#!/usr/bin/env python
# * coding: utf8 *
'''
bulldozer. A module that writes arcgis server logs to a csv with frequencies

Usage:
  bulldozer ship <machine> [--clean --email]
  bulldozer -h | --help
  bulldozer --version

Options:
  <machine>     The ArcGIS Server machine key
  --clean       Delete the logs that have been read
  --email       Email the log results
  -h --help     Show this screen.
  --version     Show version.
'''

import csv
import os
from collections import namedtuple

import requests
from docopt import docopt
from supervisor.message_handlers import SendGridHandler
from supervisor.models import MessageDetails, Supervisor

from messaging import send_email
from servers import SERVER_TOKENS

HEADERS = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
LOGS = {}
Message = namedtuple('Message', ['severity', 'source', 'code', 'message', 'methodname'])


def ship(server_name_token, remove_logs, send_mail):
    '''the main entry point for gathering the logs, summarizing them, and removing them
    '''

    if server_name_token not in SERVER_TOKENS:
        print('Machine token not found in servers.py. Did you add it?')

        return

    url, username, password = SERVER_TOKENS[server_name_token].values()

    token = get_token(username, password, url)
    if not token:
        print('Could not generate a token with the username and password provided.')

        return

    # Construct URL to query the logs
    log_url = '{}admin/logs/query'.format(url)
    clean_url = '{}admin/logs/clean'.format(url)
    log_filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), '{}.csv'.format(server_name_token))

    options = {'filter': '{}', 'token': token, 'pageSize': 10000, 'level': 'WARNING', 'f': 'json'}

    print('fetching {} log messages'.format(options['pageSize']))

    logs, more = get_log_messages(log_url, options)

    if logs is None and more is None:
        print('Could not get logs. Exiting')

        return

    if logs:
        prune(logs)

    while logs and more:
        print('fetching {} more log messages'.format(options['pageSize']))
        options['startTime'] = more
        logs, more = get_log_messages(log_url, options)
        prune(logs)

    write_logs(log_filename, LOGS)

    if send_mail:
        print('sending email')
        send_email('{} ArcGIS Server logs'.format(server_name_token), '', log_filename)

    if remove_logs:
        clean_logs(clean_url, token)

    print('done')


def get_token(username, password, server):
    '''Makes a request to the token service and stores the token information
    '''
    response_data = {}
    data = {'username': username, 'password': password, 'client': 'requestip', 'expiration': 60, 'f': 'json'}

    try:
        response = requests.post('{}admin/generateToken'.format(server), data=data, verify=False)
        response.raise_for_status()

        response_data = response.json()
    except requests.exceptions.RequestException:
        print('Unable to reach the server. Is it available?')
        return None

    status, message = return_false_for_status(response_data)

    if not status:
        print(message)
        return None

    return response_data['token']


def get_log_messages(url, data):
    '''Makes a request to the log service and returns the data along with the time to set for the next start time if there are more results
    '''
    try:
        response = requests.post(url, data=data, headers=HEADERS, verify=False)
        response.raise_for_status()

        data = response.json()
    except requests.exceptions.RequestException:
        print('Unable to reach the server. Is it available?')

        return None, None

    status, message = return_false_for_status(data)
    if not status:
        print('Error returned by operation. ', message)

        return None, None

    more_pages = False
    start_time = None
    if 'hasMore' in data.keys():
        more_pages = data['hasMore']

    if more_pages:
        start_time = data['endTime']

    return data, start_time


def clean_logs(url, token):
    '''deletes the logs for the given url and token
    '''
    data = {'token': token, 'f': 'json'}

    try:
        response = requests.post(url, data=data, headers=HEADERS, verify=False)
        response.raise_for_status()

        data = response.json()
    except requests.exceptions.RequestException:
        print('Unable to reach the server. Is it available?')

        return

    status, message = return_false_for_status(data)
    if not status:
        print('Error cleaning logs. ', message)

    print('logs cleared')


def prune(data):
    '''takes the parts from the log message that we are interested about and ignores the rest
    '''
    messages = data['logMessages']

    for message in messages:
        stripped = Message(
            message['type'],
            message['source'],
            message['code'],
            clean_message(message['message']),
            message['methodName'],
        )

        LOGS.setdefault(stripped, 0)
        LOGS[stripped] += 1


def write_logs(to_file, logs):
    print('writing to ' + to_file)

    frequencies = sorted(logs.items(), key=lambda kvp: kvp[1], reverse=True)
    with open(to_file, 'w', encoding='utf-8', newline='') as outfile:
        log_writer = csv.writer(outfile)
        log_writer.writerow(['severity', 'source', 'code', 'message', 'method name', 'frequency'])

        for message, frequency in frequencies:
            log_writer.writerow([
                message.severity, message.source, message.code, message.message, message.methodname, frequency
            ])


def return_false_for_status(json_response):
    '''json_response: string - a json payload from a server
    looks for a status in the json response and makes sure it does not contain an error
    Returns a tuple with a boolean status and a message
    '''
    if 'status' in list(json_response.keys()) and json_response['status'] == 'error':
        if 'Token Expired.' in json_response['messages']:
            return (False, 'Token expired')
        else:
            return (False, '; '.join(json_response['messages']))

    return (True, None)


def clean_message(string):
    string = ' '.join(string.splitlines())

    return string.replace(',', '-').replace('  ', ' ').replace('\'', '`')


if __name__ == '__main__':
    ARGS = docopt(__doc__)

    if ARGS['ship'] and ARGS['<machine>']:
        ship(ARGS['<machine>'], ARGS['--clean'], ARGS['--email'])
