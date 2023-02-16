from discord.ext import commands
import discord
from os import environ
from dotenv import load_dotenv
import asyncio

load_dotenv()

bot = commands.Bot(command_prefix='~', help_command=None, intents=discord.Intents.default())


async def main():
    async with bot:
        await bot.load_extension("draft_review")
        await bot.load_extension("draft_vote")
        await bot.start(environ['BotToken'])


asyncio.run(main())
