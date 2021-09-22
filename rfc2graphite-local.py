#!/bin/env python3

# curl -k --user 0061ce:94fbb0c3e890c94f -X POST -H "Content-Type: text/xml" -H "Content-Length: 165" -d "<Command><Name>device_query</Name><DeviceDetails><HardwareAddress>0x0007810001ba5640</HardwareAddress></DeviceDetails><Components><All>Y</All></Components></Command>" https://192.168.27.132/cgi-bin/post_manager
# <Command><Name>device_query</Name><DeviceDetails><HardwareAddress>0x0007810001ba5640</HardwareAddress></DeviceDetails><Components><all>Y</all></Components></Command>

import json
import requests
import socket
import time
import traceback
import xmltodict
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
from lxml import etree

class Rfc2GraphiteLocal:
    default_headers = {
        "Content-Type": "text/xml",
    }

    def __init__(self, hostname, device):
        with open('./config.json', 'r') as f:
            config = json.load(f)
            self.auth = (config.get('local_user'), config.get('local_password'))
            self.carbon_server = config.get('carbon_server')
            self.carbon_port = config.get('carbon_port')
        self.api_url = f'https://{hostname}/cgi-bin/post_manager'
        self.device = device
        # Suppress only the single warning from urllib3 needed.
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    def do_api_call(self, payload):
        content_length = str(len(payload))
        headers = self.default_headers.copy()
        headers['Content-Length'] = content_length
        r = requests.post(
            url=self.api_url,
            data=payload,
            headers=headers,
            auth=self.auth,
            verify=False,
        )
        return r.text

    def get_demand(self):
        command = etree.Element('Command')
        name = etree.Element('Name')
        name.text = 'device_query'
        command.append(name)
        
        device_details = etree.Element('DeviceDetails')
        hardware_address = etree.Element('HardwareAddress')
        hardware_address.text = self.device
        device_details.append(hardware_address)
        command.append(device_details)
        
        components = etree.Element('Components')
        all = etree.Element('all')
        all.text = 'Y'
        components.append(all)
        command.append(components)
        response = xmltodict.parse(self.do_api_call(etree.tostring(command)))
        demand = None
        try:
            variables = response.get("Device").get("Components").get("Component").get("Variables").get("Variable")
            for variable in variables:
                if variable.get("Name") == "zigbee:InstantaneousDemand":
                    demand = variable.get("Value")
                    break
        except Exception as e:
            #print(f'Encountered exception getting data: {e}')
            pass
        return demand

    def insert_data(self, offset=0):
        timestamp = datetime.now().replace(second=offset)
        while datetime.now() < timestamp:
            time.sleep(0.5)
        demand = self.get_demand()
        if demand is None:
            raise RuntimeError("Demand value not found")
        metric = f'power.instantaneous_demand.{self.device}'
        sock = socket.socket()
        sock.connect((self.carbon_server, self.carbon_port))
        s = f'{metric} {demand} {round(timestamp.timestamp())}\n'
        #print(s)
        sock.send(s.encode())

if __name__ == '__main__':
    rfc2graphite_local = Rfc2GraphiteLocal(
        hostname='192.168.27.132',
        device='0x0007810001ba5640'
    )
    for delay in [0, 15, 30, 45]:
        try:
            rfc2graphite_local.insert_data(delay)
        except Exception as e:
            traceback.print_exc()
