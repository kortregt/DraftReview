from discord.ext import commands
import discord
from os import environ
from dotenv import load_dotenv
import logging

logging_file_path = '/app/logs/discord.log'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename=logging_file_path, encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='~', help_command=None, intents=intents)

bot.load_extension("draft_review")
bot.load_extension("draft_vote")

bot.run(environ['BotToken'])