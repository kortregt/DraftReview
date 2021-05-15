from os import environ

import discord
import requests
from discord.ext import tasks


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
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    @tasks.loop(seconds=60)  # task runs every 60 seconds
    async def my_background_task(self):
        channel = self.get_channel(842662513400348684)  # channel ID goes here

        oldReviewPages = set(self.draftDict)
        self.draftDict = populate_dic()
        newReviewPages = set(self.draftDict)
        newPages = [x for x in newReviewPages if x not in oldReviewPages]
        for page in newPages:
            name = page[page.find('/', page.find('/') + 1) + 1:]
            user = page[page.find(':') + 1:page.find('/')]

            user_params = {"action": "query", "list": "users", "ususers": page[page.find(':') + 1:page.find('/')],
                           "format": "json"}
            user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
            user_json = user_request.json()
            user_id = str(user_json['query']['users'][0]['userid'])

            guild = MyClient.get_guild(self, 697848129185120256)
            role = guild.get_role(843007895573889024)

            embed = discord.Embed(title='Draft: ' + name, url=self.draftDict[page],
                                  color=discord.Color.from_rgb(36, 255, 0))
            embed.set_author(name=user, url="https://2b2t.miraheze.org/wiki/User:" + user,
                             icon_url="https://static.miraheze.org/2b2twiki/avatars/2b2twiki_" + user_id + "_l.png")

            await channel.send(role.mention, embed=embed)

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


client = MyClient()
client.run(environ['BotToken'])
