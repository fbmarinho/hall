query_xml = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:tns="http://www.witsml.org/wsdl/120" xmlns:types="http://www.witsml.org/wsdl/120/encodedTypes" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Body soap:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <q1:WMLS_GetFromStore xmlns:q1="http://www.witsml.org/message/120">
      <WMLtypeIn xsi:type="xsd:string">message</WMLtypeIn>
      <QueryIn xsi:type="xsd:string">
        <![CDATA[
          <messages xmlns="http://www.witsml.org/schemas/1series">
          <message uid="" uidWell="2c8c257a-8aa3-4c3a-a1d8-3fc240dbe5cd" uidWellbore="6bf0000c-85a4-4083-9e0e-4dd01d4a5376">
            <commonData>
            <dTimLastChange>2025-12-02T14:23:17Z</dTimLastChange>
            </commonData>
          </message>
          </messages>]]>
      </QueryIn>
      <OptionsIn xsi:type="xsd:string">returnElements=all;maxReturnNodes=2</OptionsIn>
      <CapabilitiesIn xsi:type="xsd:string"></CapabilitiesIn>
    </q1:WMLS_GetFromStore>
  </soap:Body>
</soap:Envelope>
"""

import requests
from requests.auth import HTTPBasicAuth
response = requests.post(url="https://witsmlazukseusoap.halliburton.com/halliburton/wmls.svc", data=query_xml,
    auth=HTTPBasicAuth("thales.medeiros@halliburton.com", "@S3nhaAquiEh0005"),
    headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "http://www.witsml.org/action/120/Store.WMLS_GetFromStore" })

print("Status Code:", response.status_code)
# print("Response Body:", response.text)

# Capture everything between <XMLOut> and </XMLout>
import re
match = re.search(r'<XMLout[^>]*>(.*?)</XMLout>', response.text, re.DOTALL)
if match:
    xml_output = match.group(1).replace('&lt;', '<').replace('&gt;', '>').replace('&#xD;', '').strip()
    # Beautify the XML output
    import xml.dom.minidom
    dom = xml.dom.minidom.parseString(xml_output)
    pretty_xml_as_string = dom.toprettyxml()
    print("Extracted XML Output:", pretty_xml_as_string)