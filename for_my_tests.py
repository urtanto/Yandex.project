import urllib
import requests
import pprint
import json


ROOT_ID = "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1"
params = urllib.parse.urlencode({
    "dateStart": "2022-02-01T00:00:00Z"
})
ans = requests.request("POST", f"http://127.0.0.1:5000/delete/1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2")
print(ans.status_code, ans.text)
pprint.pprint(json.loads(ans.text))
