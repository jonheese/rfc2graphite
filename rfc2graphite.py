#!/usr/bin/env python3

import json
import requests
import socket


class Rfc2Graphite:
    API_URL = 'https://api.rainforestcloud.com/rest'

    def __init__(self):
        with open('./config.json', 'r') as f:
            config = json.load(f)
            self.auth = (config.get('login'), config.get('password'))
            self.carbon_server = config.get('carbon_server')
            self.carbon_port = config.get('carbon_port')

        if 'login' not in config.keys() or 'password' not in config.keys():
            raise RuntimeError(
                'Login and password must be specified in config.json'
            )
        self.default_headers = {
            'accept': 'application/json',
        }
        self.devices = []

    def do_api_call(
            self,
            endpoint=None,
            method='GET',
            payload=None,
            headers=None,
    ):
        if not headers:
            headers = self.default_headers
        if endpoint is None:
            raise RuntimeError('API endpoint must be provided')
        url = f'{self.API_URL}/{endpoint}'
        if method == 'GET':
            r = requests.get(
                url,
                headers=headers,
                auth=self.auth,
            )
        elif method == 'POST':
            r = requests.post(
                url,
                data=payload,
                headers=headers,
                auth=self.auth,
            )
        else:
            raise RuntimeError(f'Method {method} unsupported')
        if r.status_code != requests.codes.ok:
            raise RuntimeError(
                f'Error encountered performing {method} to {url} ' +
                'with headers:\n' + json.dumps(headers, indent=2) + '\n' +
                json.dumps(r.json(), indent=2)
            )
        return r.json()

    def get_devices(self):
        data = self.do_api_call(
            endpoint='user/current',
        )
        self.devices = data.get('devices')

    def insert_data(self):
        base_metric = 'power.instantaneous_demand'
        if not self.devices:
            self.get_devices()
        sock = socket.socket()
        sock.connect((self.carbon_server, self.carbon_port))
        for device in self.devices:
            device_guid = device.get('deviceGuid')
            metric = f'{base_metric}.{device_guid}'
            data = self.do_api_call(
                endpoint=f'data/metering/demand/latest/{device_guid}',
            )
            for result in data:
                entries = result.get('entries')
                if isinstance(entries, dict):
                    for timestamp in entries.keys():
                        ts = int(timestamp) / 1000
                        s = f'{metric} {entries.get(timestamp)} {ts}\n'
                        sock.send(s.encode())
        sock.close()


if __name__ == '__main__':
    rfc2graphite = Rfc2Graphite()
    rfc2graphite.insert_data()
