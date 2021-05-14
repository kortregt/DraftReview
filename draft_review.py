import discord
from discord.ext import tasks
from os import environ
import json
import requests


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # an attribute we can access from our task
        draftDict = {

        }

        params = {"action": "query", "list": "categorymembers", "cmtitle": "Category:Drafts_awaiting_review",
                  "format": "json"}
        url = 'https://2b2t.miraheze.org/'

        request = requests.get(url + "w/api.php", params=params)
        json_data = request.json()

        pages = json_data['query']['categorymembers']
        for i in range(len(pages)):
            title = pages[i]['title']
            link = url + "wiki/" + pages[i]['title']
            draftDict[title] = link

        # start the task to run in the background
        self.my_background_task.start()

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    @tasks.loop(hours=1)  # task runs every 60 seconds
    async def my_background_task(self):
        channel = self.get_channel(842627063856103444)  # channel ID goes here
        await channel.send(self.draftDict)

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


client = MyClient()
client.run(environ['BotToken'])
