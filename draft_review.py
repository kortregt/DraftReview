import discord
from discord.ext import tasks

import pywikibot
from pywikibot import pagegenerators


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # an attribute we can access from our task
        self.draftDict = {

        }

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
        self.counter += 1
        await channel.send(self.counter)

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


client = MyClient()
client.run('ODQyNTMxNjAwNTMzMDI4OTA0.YJ2qsw.vErUzXHlXLfeU923mTj91J7zVe4')
