import requests
from bs4 import BeautifulSoup
url="http://www.mouser.com/service/searchapi.asmx"
#headers = {'content-type': 'application/soap+xml'}

body = """<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <MouserHeader xmlns="http://api.mouser.com/service">
      <AccountInfo>
        <PartnerID>43b05c82-e4b7-47d2-90f0-a53dcd0930ab</PartnerID>
      </AccountInfo>
    </MouserHeader>
  </soap12:Header>
  <soap12:Body>
    <SearchByPartNumber xmlns="http://api.mouser.com/service">
      <mouserPartNumber>511-STM32F427IGH7</mouserPartNumber>
      <partSearchOptions>2</partSearchOptions>
    </SearchByPartNumber>
  </soap12:Body>
</soap12:Envelope>"""
encoded_request = body.encode('utf-8')
headers = {'Content-Type': 'application/soap+xml; charset=utf-8'} #'content-length': str(len(encoded_request))}
response = requests.post(url,data=body,headers=headers)
#print (response.content)
res = response.content
print(res)

import xml.etree.ElementTree as ET
root = ET.fromstring(res)

namespaces = {
    'soap': 'http://www.w3.org/2003/05/soap-envelope',
    'a': 'http://api.mouser.com/service',
    }

names = root.findall(
    './soap:Body'
    '/a:SearchByPartNumberResponse'
    '/a:SearchByPartNumberResult'
    '/a:Parts'
    '/a:MouserPart'
    '/a:ProductDetailUrl',
    namespaces,
    )
url = ''
for name in names:
    url = name.text
    print(name.text)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
    }
page = requests.get(url, headers=headers, timeout=10)
data = BeautifulSoup(page.text, 'html.parser')
manufacturer_table = data.find(class_='div-table-body')
print(data)
manu = manufacturer_table.find_all('label')
print(manu.text.strip())



import http.client
import requests
import json
from mrp_system.models import DigiKeyAPI

digi = DigiKeyAPI.objects.get(name="DigiKey")

API_ENDPOINT = "https://sso.digikey.com/as/token.oauth2"

data = {'client_id': '73432ca9-e8ba-4965-af17-a22107f63b35',
        'client_secret': 'G2rQ1cM8yM4gV6rW2nA1wL2yF7dN4sX4fJ2lV6jE5uT0bB0uG8',
        'refresh_token': digi.refresh_token,
        'grant_type': 'refresh_token'
        }
r = requests.post(url = API_ENDPOINT, data=data)
response = r.json()
refreshToken = response['refresh_token']
accessToken = response['access_token']
setattr(digi,"refresh_token",refreshToken)
setattr(digi,"access_token",accessToken)
digi.save()
            
conn = http.client.HTTPSConnection("api.digikey.com")

headers = {
    'x-ibm-client-id': '73432ca9-e8ba-4965-af17-a22107f63b35',
    'authorization': digi.access_token,
    'accept': "application/json"
    }

conn.request("GET", "/services/barcode/v1/productbarcode/2731164000000050837316"
             , headers=headers)

res = conn.getresponse()
data = res.read().decode("utf-8")
part = json.loads(data)
number = part['DigiKeyPartNumber']
print(number)

