import discord
from discord.ext import tasks
from os import environ
import json
import requests


def populate_dic():
    pageDic = {}
    params = {"action": "query", "list": "categorymembers", "cmtitle": "Category:Drafts_awaiting_review",
              "format": "json"}
    url = 'https://2b2t.miraheze.org/'

    request = requests.get(url + "w/api.php", params=params)
    json_data = request.json()

    pages = json_data['query']['categorymembers']
    for i in range(len(pages)):
        title = pages[i]['title']
        link = url + "wiki/" + pages[i]['title']
        pageDic[title] = link

    return pageDic


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # an attribute we can access from our task
        self.draftDict = {}

        # start the task to run in the background
        self.my_background_task.start()

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    @tasks.loop(seconds=60)  # task runs every 60 seconds
    async def my_background_task(self):
        channel = self.get_channel(842662513400348684)  # channel ID goes here

        oldReviewPages = set(self.draftDict)
        self.draftDict = populate_dic()
        newReviewPages = set(self.draftDict)
        newPages = [x for x in newReviewPages if x not in oldReviewPages]

        for page in newPages:
            name = page[page.find('/', page.find('/') + 1)+1:]
            author = 'Submitted by ' + page[page.find(':')+1:page.find('/')]
            embed = discord.Embed(title='Draft of '+name, url=self.draftDict[page], description=author, color=discord.
                                  Color.from_rgb(0, 255, 1))
            await channel.send(embed=embed)

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


client = MyClient()
client.run(environ['BotToken'])
