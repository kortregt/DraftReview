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
        
        # Create bot instance
        bot = SyncBot()
        
        # Login but don't start processing events
        await bot.login(token)
        
        # Get the guild
        guild_id = 697848129185120256
        guild = await bot.fetch_guild(guild_id)
        
        if not guild:
            print(f"Error: Could not find guild with ID {guild_id}")
            sys.exit(1)
            
        print(f"Syncing commands to guild: {guild.name}")
        
        # Sync commands
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        
        print("Commands synced successfully!")
        
    except KeyError:
        print("Error: BotToken environment variable not set")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        # Always try to close the bot connection
        try:
            await bot.close()
        except:
            pass

if __name__ == "__main__":
    print("Starting command sync...")
    asyncio.run(sync_commands())
