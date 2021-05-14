import requests
params = {"action": "query", "list": "categorymembers", "cmtitle": "Category:Drafts_awaiting_review", "format": "json"}

request = requests.get("https://2b2t.miraheze.org/w/api.php", params=params)
json_data = request.json()

pages = json_data['query']['categorymembers']
for i in range(len(pages)):
    print(pages[i]['title'])
