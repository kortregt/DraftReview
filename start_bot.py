from discord.ext import commands
from os import environ
from dotenv import load_dotenv

load_dotenv()

bot = commands.Bot(command_prefix='~', help_command=None)

bot.load_extension("draft_review")
bot.load_extension("draft_vote")

bot.run(environ['BotToken'])
