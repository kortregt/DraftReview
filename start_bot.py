import asyncio
from discord.ext import commands
import discord
from os import environ, makedirs, path
from dotenv import load_dotenv
import logging
import os

# Ensure logs directory exists
log_dir = '/app/logs'
makedirs(log_dir, exist_ok=True)
logging_file_path = path.join(log_dir, 'discord.log')

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename=logging_file_path, encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()

# Setup intents
intents = discord.Intents.default()
intents.message_content = True


class DraftReviewBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing bot...")
        super().__init__(
            command_prefix='~',
            help_command=None,
            intents=intents
        )

    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        logger.info("Setting up bot...")
        logger.info(f"Current directory: {path.abspath('.')}")
        logger.info(f"Available files: {[f for f in os.listdir('.') if f.endswith('.py')]}")

        try:
            logger.info("Loading extensions...")
            await self.load_extension("draft_review")
            await self.load_extension("draft_vote")
            logger.info("Extensions loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load extensions: {e}", exc_info=True)
            raise

    async def on_ready(self):
        """Event that runs when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("Bot is ready!")
        # Check commands after everything is loaded
        for cog_name, cog in self.cogs.items():
            commands = [cmd for cmd in cog.walk_commands()]
            logger.info(f"Cog {cog_name} has commands: {[cmd.name for cmd in commands]}")


async def main():
    async with DraftReviewBot() as bot:
        await bot.start(environ['BotToken'])


# Run the bot
try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("Bot shutdown by user")
except Exception as e:
    logger.error(f"Bot crashed: {str(e)}", exc_info=True)