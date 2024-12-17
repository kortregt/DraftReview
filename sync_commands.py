#!/usr/bin/env python3
import discord
from discord.ext import commands
import asyncio
import os
import sys

async def sync_commands():
    """Sync slash commands to the guild."""
    try:
        # Get token from environment
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("Error: DISCORD_TOKEN environment variable not set")
            sys.exit(1)

        # Initialize bot with all intents
        intents = discord.Intents.all()
        bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Load cogs
        bot.load_extension('draft_review')
        bot.load_extension('draft_vote')
        
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
