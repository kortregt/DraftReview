import asyncio
from discord.ext import commands
import discord
from os import environ, makedirs, path
from dotenv import load_dotenv
import logging

# Ensure logs directory exists
log_dir = '/app/logs'
makedirs(log_dir, exist_ok=True)
logging_file_path = path.join(log_dir, 'discord.log')

# Setup logging
logging.basicConfig(level=logging.INFO)
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
        super().__init__(
            command_prefix='~',
            help_command=None,
            intents=intents
        )
        # Add reconnect settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # Start with 5 second delay
    
    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        print('waiting...')  # Add the waiting message back
        await self.load_extension("draft_review")
        await self.load_extension("draft_vote")
        logger.info("Bot extensions loaded")

    async def on_ready(self):
        """Event that runs when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.reconnect_attempts = 0  # Reset reconnect attempts on successful connection

    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle any uncaught exceptions."""
        logger.error(f"Error in {event_method}", exc_info=True)
        
        if "connect" in event_method and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))  # Exponential backoff
            logger.info(f"Attempting reconnect {self.reconnect_attempts} in {delay} seconds...")
            await asyncio.sleep(delay)
            try:
                await self.start(environ['BotToken'])
            except Exception as e:
                logger.error(f"Reconnect attempt failed: {str(e)}")
        else:
            logger.error("Max reconnect attempts reached or non-connection error occurred")

async def main():
    print('waiting...')  # Add waiting message at startup
    bot = DraftReviewBot()
    try:
        async with bot:
            await bot.start(environ['BotToken'])
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}", exc_info=True)
    finally:
        if not bot.is_closed():
            await bot.close()

# Run the bot
try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("Bot shutdown by user")
except Exception as e:
    logger.error(f"Bot crashed: {str(e)}", exc_info=True)