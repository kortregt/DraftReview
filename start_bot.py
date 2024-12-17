import asyncio
from discord.ext import commands
import discord
from os import environ, makedirs, path
from dotenv import load_dotenv
import logging
import os
import traceback
import sys

# Ensure logs directory exists
log_dir = '/app/logs'
makedirs(log_dir, exist_ok=True)
logging_file_path = path.join(log_dir, 'discord.log')

# Setup logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

# Add stdout handler to see logs directly in console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(filename=logging_file_path, encoding='utf-8', mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(file_handler)

load_dotenv()

class DraftReviewBot(commands.Bot):
    def __init__(self):
        print("Bot initialization starting...")  # Direct print for debugging
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix='~',
            help_command=None,
            intents=intents
        )
        print("Bot initialization complete")  # Direct print for debugging

    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        print("\n=== Starting Setup ===")  # Direct print for debugging
        print(f"Current working directory: {os.getcwd()}")
        print(f"Files in directory: {os.listdir('.')}")
        
        try:
            print("\nAttempting to load draft_review...")
            await self.load_extension("draft_review")
            print("draft_review loaded successfully")
            
            print("\nAttempting to load draft_vote...")
            await self.load_extension("draft_vote")
            print("draft_vote loaded successfully")
            
            print("\nExtensions loaded, checking cogs...")
            print(f"Registered cogs: {list(self.cogs.keys())}")
            for cog_name, cog in self.cogs.items():
                print(f"Commands in {cog_name}: {[cmd.name for cmd in cog.get_commands()]}")
            
        except Exception as e:
            print(f"\nERROR loading extensions: {e}")
            print("Full traceback:")
            traceback.print_exc()
            raise

    async def on_ready(self):
        """Event that runs when the bot is ready."""
        print("\n=== Bot Ready ===")
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Registered cogs: {list(self.cogs.keys())}")
        for cog_name, cog in self.cogs.items():
            print(f"Commands in {cog_name}: {[cmd.name for cmd in cog.get_commands()]}")

async def main():
    bot = DraftReviewBot()
    async with bot:
        try:
            print("\nStarting bot...")
            await bot.start(environ['BotToken'])
        except Exception as e:
            print(f"Error starting bot: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print("=== Starting Bot Process ===")
    asyncio.run(main())