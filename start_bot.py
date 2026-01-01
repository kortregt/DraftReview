from discord.ext import commands
import discord
from os import environ, makedirs, path
from dotenv import load_dotenv
import logging

# Ensure logs directory exists
makedirs('/app/logs', exist_ok=True)
logging_file_path = '/app/logs/discord.log'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename=logging_file_path, encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.polls = True

# Create bot
bot = commands.Bot(command_prefix='~', help_command=None, intents=intents)

@bot.event
async def on_ready():
    """Log when bot is ready"""
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info(f'Bot ready - logged in as {bot.user} (ID: {bot.user.id})')

# Load extensions
try:
    bot.load_extension("draft_review")
    bot.load_extension("draft_vote")
    print('Extensions loaded')
except Exception as e:
    logger.error(f'Failed to load extensions: {str(e)}')
    raise

# Run bot
try:
    print('Starting bot...')
    bot.run(environ['BotToken'])
except KeyboardInterrupt:
    print('Bot shutdown by user')
except Exception as e:
    logger.error(f'Bot failed to start: {str(e)}')
    raise