import urllib
import requests
import pprint
import json

IMPORT_BATCHES = [
    {
        "items": [
            {
                "type": "CATEGORY",
                "name": "Товары",
                "id": "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
                "parentId": None,
                "children": []
            }
        ],
        "updateDate": "2022-02-01T12:00:00Z"
    }, {
        "items": [
            {
                "type": "CATEGORY",
                "name": "Товары",
                "id": "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
                "parentId": None,
                "children": []
            }
        ],
        "updateDate": "2022-02-02T12:00:00Z"
    }
]

ROOT_ID = "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1"
params = urllib.parse.urlencode({
    "dateStart": "2022-02-01T00:00:00Z"
})
ans = requests.request("POST", f"http://127.0.0.1:5000/imports", json=IMPORT_BATCHES[0])
print(ans.status_code, ans.text)
ans = requests.request("POST", f"http://127.0.0.1:5000/imports", json=IMPORT_BATCHES[1])
print(ans.status_code, ans.text)
# pprint.pprint(json.loads(ans.text))
