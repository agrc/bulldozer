#!/usr/bin/env python
# * coding: utf8 *
'''
main.py
A module that writes arcgis server logs to a csv with frequencies
'''

import csv
import getpass
import os
import sys
from collections import namedtuple

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
SERVER_TOKENS = {
    'key': 'https://url:6443/arcgis/',
}
LOGS = {}
Message = namedtuple('Message', ['severity', 'source', 'code', 'message', 'methodname'])


def main():
    '''the main entry point for gathering the logs, summarizing them, and removing them
    '''
    username = input('Enter user name: ')
    password = getpass.getpass('Enter password: ')
    server_name_token = input('Enter short machine name (eg. `key`): ')

    token = get_token(username, password, SERVER_TOKENS[server_name_token])
    if not token:
        print('Could not generate a token with the username and password provided.')

        return

    # Construct URL to query the logs
    log_url = '{}admin/logs/query'.format(SERVER_TOKENS[server_name_token])
    clean_url = '{}admin/logs/clean'.format(SERVER_TOKENS[server_name_token])
    log_filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), '{}.csv'.format(server_name_token))

    options = {'filter': '{}', 'token': token, 'pageSize': 10000, 'level': 'WARNING', 'f': 'json'}

    print('fetching {} log messages'.format(options['pageSize']))

    logs, more = get_log_messages(log_url, options)

    if logs:
        prune(logs)

    while logs and more:
        print('fetching {} more log messages'.format(options['pageSize']))
        options['startTime'] = more
        logs, more = get_log_messages(log_url, options)
        prune(logs)

    write_logs(log_filename, LOGS)
    clean_logs(clean_url, token)

    print('done')


def get_token(username, password, server):
    '''Makes a request to the token service and stores the token information
    '''
    data = {'username': username, 'password': password, 'client': 'requestip', 'expiration': 60, 'f': 'json'}

    response = requests.post('{}admin/generateToken'.format(server), data=data, verify=False)
    response.raise_for_status()

    response_data = response.json()
    status, message = return_false_for_status(response_data)

    if not status:
        print(message)

    return response_data['token']


def get_log_messages(url, data):
    '''Makes a reqeust to the log service and returns the data along with the time to set for the next start time if there are more results
    '''
    response = requests.post(url, data=data, headers=HEADERS, verify=False)
    response.raise_for_status()

    data = response.json()

    status, message = return_false_for_status(data)
    if not status:
        print('Error returned by operation. ' + message)

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
    response = requests.post(url, data=data, headers=HEADERS, verify=False)
    response.raise_for_status()

    data = response.json()

    status, message = return_false_for_status(data)
    if not status:
        print('Error cleaning logs. ' + message)

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
    with open(to_file, 'w', newline='') as outfile:
        log_writer = csv.writer(outfile)
        log_writer.writerow(['severity', 'source', 'code', 'message', 'method name', 'frequency'])

        for message, frequency in frequencies:
            log_writer.writerow([message.severity, message.source, message.code, message.message, message.methodname, frequency])


def return_false_for_status(json_response):
    '''json_reponse: string - a json payload from a server
    looks for a status in the json reponse and makes sure it does not contain an error
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
    sys.exit(main())
