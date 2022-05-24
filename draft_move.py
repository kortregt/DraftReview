import requests
from os import environ


def move_page(user, name):
    S = requests.Session()

    URL = "https://2b2t.miraheze.org/w/api.php"

    # Step 1: Retrieve a login token
    PARAMS_1 = {
        'action': "query",
        'meta': "tokens",
        'type': "login",
        'format': "json"
    }

    R = S.get(url=URL, params=PARAMS_1)
    DATA = R.json()

    LOGIN_TOKEN = DATA['query']['tokens']['logintoken']

    # Step 2: Send a POST request to log in.
    # See https://www.mediawiki.org/wiki/API:Login for more
    # information on log in methods.

    PARAMS_2 = {
        'action': "login",
        'lgname': "2b2tWikiBot@2b2tWikiBot",
        'lgpassword': environ['2b2tWikiBotPassword'],
        'lgtoken': LOGIN_TOKEN,
        'format': "json"
    }

    R = S.post(URL, data=PARAMS_2)

    # Step 3: While logged in, retrieve a CSRF token
    PARAMS_3 = {
        'action': "query",
        'meta': "tokens",
        'format': "json"
    }

    R = S.get(url=URL, params=PARAMS_3)
    DATA = R.json()

    CSRF_TOKEN = DATA["query"]["tokens"]["csrftoken"]

    # Step 4: Send a POST request to move the page
    PARAMS_4 = {
        "action": "move",
        "format": "json",
        "from": f"User:{user}/Drafts/{name}",
        "to": name,
        "reason": "Approved draft",
        "movetalk": "1",
        "noredirect": "1",
        "token": CSRF_TOKEN
    }

    R = S.post(url=URL, data=PARAMS_4)
    DATA = R.text

    print(DATA)
