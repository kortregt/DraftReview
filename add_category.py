import requests
from os import environ
from dotenv import load_dotenv

load_dotenv()


def add_category(user, name, categories):
    text = ""
    category_list = categories.split(",")
    category_list = ["[[Category:"+category.strip()+"]]" for category in category_list]

    S = requests.Session()

    URL = "https://2b2t.miraheze.org/w/api.php"

    # Step 0: Get most recent revision content of target page
    PARAMS_0 = {
        "action": "query",
        "prop": "revisions",
        "titles": f"User:{user}/Drafts/{name}",
        "rvprop": "content",
        "formatversion": "2",
        "format": "json"
    }

    R = S.get(url=URL, params=PARAMS_0)
    DATA = R.json()
    PAGES = DATA["query"]["pages"]
    for page in PAGES:
        REVISIONS = page["revisions"]
        for revision in REVISIONS:
            text = revision["content"]

    text += "\n\n"
    for category in category_list:
        text += (category + "\n")
    text = text.rstrip()

    # Step 1: GET request to fetch login token
    PARAMS_1 = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    }

    R = S.get(url=URL, params=PARAMS_1)
    DATA = R.json()

    LOGIN_TOKEN = DATA['query']['tokens']['logintoken']

    # Step 2: POST request to log in. Use of main account for login is not
    # supported.
    PARAMS_2 = {
        "action": "login",
        "lgname": "2b2tWikiBot@2b2tWikiBot",
        "lgpassword": environ['2b2tWikiBotPassword'],
        "lgtoken": LOGIN_TOKEN,
        "format": "json"
    }

    R = S.post(URL, data=PARAMS_2)

    # Step 3: GET request to fetch CSRF token
    PARAMS_3 = {
        "action": "query",
        "meta": "tokens",
        "format": "json"
    }

    R = S.get(url=URL, params=PARAMS_3)
    DATA = R.json()

    CSRF_TOKEN = DATA['query']['tokens']['csrftoken']

    # Step 4: POST request to edit a page
    PARAMS_4 = {
        "action": "edit",
        "title": f"User:{user}/Drafts/{name}",
        "bot": "1",
        "token": CSRF_TOKEN,
        "format": "json",
        "text": text,
        "summary": "Added categories"
    }

    R = S.post(URL, data=PARAMS_4)
    DATA = R.json()

    print(DATA)
