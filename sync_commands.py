#!/usr/bin/env python3
import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
import sys

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
        print(f"Python path: {sys.path}")  # Debug print
    
    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        print("\nIn setup_hook")  # Debug print
        print("Loading extensions...")
        try:
            print(f"Current directory: {os.getcwd()}")  # Debug print
            print(f"Directory contents: {os.listdir('.')}")  # Debug print
            
            # Try to load extensions
            for ext in ["draft_review", "draft_vote"]:
                print(f"\nTrying to load {ext}...")  # Debug print
                try:
                    await self.load_extension(ext)
                    print(f"✓ Successfully loaded {ext}")
                    if ext in self.cogs:
                        print(f"Found cog {ext} in self.cogs")
                        for command in self.cogs[ext].walk_commands():
                            print(f"  Command found: {command.name}")
                except Exception as e:
                    print(f"✗ Failed to load {ext}: {str(e)}")
                    raise

        except Exception as e:
            print(f"Error during extension loading: {e}")
            raise

    async def on_ready(self):
        """Runs when the bot is fully connected to Discord."""
        print(f"\nConnected as {self.user} (ID: {self.user.id})")
        
        # Get the guild
        guild_id = 697848129185120256
        guild = self.get_guild(guild_id)
        
        if guild:
            print(f"Found guild: {guild.name} ({guild_id})")
            try:
                print("\nSyncing commands...")
                print(f"Current cogs: {list(self.cogs.keys())}")  # Debug print
                print(f"Current commands: {[cmd.name for cmd in self.commands]}")
                commands = await self.sync_commands(guild_ids=[guild_id])
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
                print(f"Error type: {type(e)}")  # Debug print
                import traceback
                traceback.print_exc()  # Debug print
        else:
            print(f"Could not find guild with ID: {guild_id}")
            print("Available guilds:", [g.name for g in self.guilds])
        
        # Clean shutdown
        try:
            await self.close()
        except Exception as e:
            print(f"Error during shutdown: {e}")

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
        bot = SyncBot()
        async with bot:
            await bot.start(token)
            
    except Exception as e:
        print(f"Fatal error during setup: {str(e)}")
        raise

if __name__ == "__main__":
    print("=== Discord Command Sync Script ===\n")
    asyncio.run(sync_commands())