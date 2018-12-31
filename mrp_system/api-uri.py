##POST /as/token.oauth2 HTTP/1.1
##                    Host: sso.digikey.com
##                    Content-Type: application/x-www-form-urlencoded
##
##                    client_id={your_client_id}&
##                    client_secret={your_client_secret}&
##                    refresh_token=123Asfeksodk/jkdsoieDSioIOS-483LidkOOl&
##                    grant_type=refresh_token

import requests
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
print(response)
refreshToken = response['refresh_token']
setattr(digi,"refresh_token",refreshToken)
digi.save()
#DigiKeyAPI.objects.create(name="DigiKey", refresh_token=refresh_token)


#https://sso.digikey.com/as/authorization.oauth2?response_type=code&client_id=73432ca9-e8ba-4965-af17-a22107f63b35&redirect_uri=https://127.0.0.1:8000/mrp/oauth/
