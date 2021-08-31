import getpass
import time
import sys
import requests


def main():
    userName = str(input("Enter your username: "))
    password = str(getpass.getpass("Enter your password: "))
    cloud_id = str(input("Enter EAGLE cloud ID: "))

    getSubdevices(userName, password, cloud_id)


def getSubdevices(userName, password, cloud_id):
    url = 'https://api.rainforestcloud.com/rest/device/d8d5b9' + cloud_id + '/subdevice'
    myResponse = requests.get(url, auth=(userName, password))

    print(myResponse.json())


main()
