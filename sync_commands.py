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
        print("\nLoading extensions...")
        try:
            # First check if files exist
            for ext in ["draft_review", "draft_vote"]:
                if os.path.exists(f"{ext}.py"):
                    print(f"Found {ext}.py")
                else:
                    print(f"WARNING: Could not find {ext}.py")

            # Try to load extensions
            for ext in ["draft_review", "draft_vote"]:
                try:
                    await self.load_extension(ext)
                    print(f"✓ Successfully loaded {ext}")
                    # Print the commands from this extension
                    if ext in self.cogs:
                        cog = self.cogs[ext]
                        print(f"  Commands in {ext}:")
                        for cmd in cog.walk_commands():
                            print(f"  - {cmd.name}")
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
                print("Current commands before sync:", [cmd.name for cmd in self.commands])
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
        else:
            print(f"Could not find guild with ID: {guild_id}")
            print("Available guilds:", [g.name for g in self.guilds])
        
        # Properly close the session
        await self.close()
        for session in self._connection.http._session:
            await session.close()

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