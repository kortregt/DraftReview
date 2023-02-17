from discord.ext import commands
import discord
from os import environ
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='~', help_command=None, intents=intents)

bot.load_extension("draft_review")
bot.load_extension("draft_vote")

bot.run(environ['BotToken'])
