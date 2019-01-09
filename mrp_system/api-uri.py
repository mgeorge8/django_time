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
                               
##for manufacturer in manufacturer_table_list:
##    header = manufacturer.text.strip()
##    row = manufacturer.find_next_sibling().text.strip()
##    if header == 'Manufacturer':
##        manu = row
##    if header == 'Manufacturer Part Number':
##        man_partNumber = row
##    if header == 'Detailed Description':
##        detailed_descript = row
##
##manu, created = Manufacturer.objects.get_or_create(name=manu)
##
##part_table = data.find(id="product-attribute-table")
##part_table_list = part_table.find_all("th")
##part_attr = {}
##for part in part_table_list:
##    header = part.text.strip()
##    row = part.find_next_sibling().text.strip()
##    part_attr[header] = row
##    
##part = Part.objects.create(partType=partType, description=detailed_descript)
##for field in partType.field.all():
##    name = part_attr.get(field.name)
##    if name == 'null' or name is None or name == '-':
##        name = ''
##    f = field.fields
##    setattr(part, f, name)
##
##part.save()
##
##ManufacturerRelationship.objects.create(part=part, manufacturer=manu,
##                                    partNumber=man_partNumber)
