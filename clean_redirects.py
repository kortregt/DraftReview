import requests
from os import environ
from dotenv import load_dotenv

load_dotenv()


def clean(user, name):
    S = requests.Session()

    URL = "https://2b2t.miraheze.org/w/api.php"

    # Query list of redirects to the page
    PARAMS = {
        "action": "query",
        "format": "json",
        "titles": f"User:{user}/Drafts/{name}",
        "prop": "redirects"
    }

    R = S.get(url=URL, params=PARAMS)
    DATA = R.json()

    PAGES = DATA["query"]["pages"]
    for page in PAGES:
        if "redirects" not in PAGES[page]:
            return

    # Delete redirects
    # Step1: Retrieve login token
    PARAMS_0 = {
        'action': "query",
        'meta': "tokens",
        'type': "login",
        'format': "json"
    }

    R = S.get(url=URL, params=PARAMS_0)
    DATA = R.json()

    LOGIN_TOKEN = DATA['query']['tokens']['logintoken']

    # Step2: Send a post request to login. Use of main account for login is not
    # supported. Obtain credentials via Special:BotPasswords
    # (https://www.mediawiki.org/wiki/Special:BotPasswords) for lgname & lgpassword
    PARAMS_1 = {
        'action': "login",
        'lgname': "2b2tWikiBot@2b2tWikiBot",
        'lgpassword': environ['2b2tWikiBotPassword'],
        'lgtoken': LOGIN_TOKEN,
        'format': "json"
    }

    R = S.post(URL, data=PARAMS_1)

    # Step 3: When logged in, retrieve a CSRF token
    PARAMS_2 = {
        'action': "query",
        'meta': "tokens",
        'format': "json"
    }

    R = S.get(url=URL, params=PARAMS_2)
    DATA = R.json()

    CSRF_TOKEN = DATA['query']['tokens']['csrftoken']

    # Step 4: Send a post request to delete a page
    for page in PAGES:
        PARAMS_3 = {
            'action': "delete",
            'title': (PAGES[page]["redirects"][0]["title"]),
            'token': CSRF_TOKEN,
            'format': "json"
        }

        R = S.post(URL, data=PARAMS_3)
        DATA = R.json()

        print(DATA)
