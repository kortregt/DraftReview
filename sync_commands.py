#!/usr/bin/env python3
import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

class SyncBot(commands.Bot):
    def __init__(self):
        print("Initializing bot...")
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            help_command=None,
            intents=intents
        )
    
    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        print("Loading extensions...")
        try:
            await self.load_extension("draft_review")
            print("✓ Loaded draft_review")
            await self.load_extension("draft_vote")
            print("✓ Loaded draft_vote")
        except Exception as e:
            print(f"Error loading extensions: {e}")
            raise

async def sync_commands():
    """Sync slash commands to the guild."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get token from environment
        token = os.environ.get('BotToken')
        if not token:
            raise ValueError("BotToken environment variable not set")
        
        print("Starting command sync...")
        
        # Create and set up bot
        async with SyncBot() as bot:
            # Login but don't start processing events
            print("Logging in...")
            await bot.login(token)
            
            # Get the guild
            guild_id = 697848129185120256
            guild = bot.get_guild(guild_id)
            
            if guild:
                print(f"Found guild: {guild.name} ({guild_id})")
            else:
                print(f"Could not find guild with ID: {guild_id}")
                print("Available guilds:", [g.name for g in bot.guilds])
            
            print("\nSyncing commands...")
            try:
                commands = await bot.sync_commands(guild_ids=[guild_id])
                if commands:
                    print("\nSuccessfully synced commands:")
                    for cmd in commands:
                        print(f"- {cmd.name}: {cmd.description}")
                else:
                    print("No commands were synced. Check if commands are properly defined in cogs.")
                
            except discord.errors.Forbidden as e:
                print(f"ERROR: Bot lacks permissions to sync commands: {e}")
            except Exception as e:
                print(f"ERROR during command sync: {e}")
            
    except Exception as e:
        print(f"Fatal error during setup: {str(e)}")
        raise

if __name__ == "__main__":
    print("=== Discord Command Sync Script ===\n")
    asyncio.run(sync_commands())