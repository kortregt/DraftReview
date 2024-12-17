#!/usr/bin/env python3
import discord
from discord.ext import commands
import asyncio
import os
import sys
from os import environ
from dotenv import load_dotenv

class SyncBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            help_command=None,
            intents=intents
        )
    
    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        await self.load_extension("draft_review")
        await self.load_extension("draft_vote")

async def sync_commands():
    """Sync slash commands to the guild."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get token from environment
        token = environ['BotToken']
        
        # Create and set up bot
        async with SyncBot() as bot:
            # Login but don't start processing events
            await bot.login(token)
            
            # Get the guild
            guild_id = 697848129185120256
            
            print(f"Syncing commands to guild ID: {guild_id}")
            
            # Sync commands specifically to this guild
            await bot.sync_commands(
                guild_ids=[guild_id],
                force=True,  # Force sync regardless of command state
                register_guild_commands=True,
                delete_existing=True  # Clean up any old commands
            )
            
            print("Commands synced successfully!")
            
    except KeyError:
        print("Error: BotToken environment variable not set")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting command sync...")
    asyncio.run(sync_commands())
