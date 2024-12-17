import discord
import requests
from discord.ext import tasks, commands
import datetime
import re
import os
from os import path

import draft_deny
import draft_move
import page_move
import clean_redirects
import add_category
from draft_database import DraftDatabase

good_url = re.compile('.+Drafts/.+')

threads = set()


def populate_db(db: DraftDatabase):
    """Populate the database with drafts from the wiki API."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Drafts_awaiting_review",
        "cmlimit": "100",
        "format": "json"
    }
    url = 'https://2b2t.miraheze.org/'

    request = requests.get(url + "w/api.php", params=params)
    request.raise_for_status()
    json_data = request.json()

    pages = json_data['query']['categorymembers']
    for page in pages:
        title = page['title']
        link = url + "wiki/" + page['title']
        link = link.replace(" ", "_")
        db.add_draft(title, link)


class DraftBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        db_path = os.getenv('DATABASE_PATH')
        self.db = DraftDatabase(db_path)
        self.fetch_draft.start()

    def cog_unload(self):
        self.fetch_draft.cancel()

    @tasks.loop(seconds=60)
    async def fetch_draft(self, *args):
        # channel = self.bot.get_channel(1075585762243915787)  # channel ID goes here (bot testing)
        channel = self.bot.get_channel(1150122572294410441)  # channel ID goes here (draft-menders)

        old_drafts = set(self.db.get_all_drafts().keys())
        try:
            populate_db(self.db)
            new_drafts = set(self.db.get_all_drafts().keys())
            new_pages = [x for x in new_drafts if x not in old_drafts]

            for page in new_pages:
                name = page[page.find('/', page.find('/') + 1) + 1:]
                user = page[page.find(':') + 1:page.find('/')]
                if re.fullmatch(good_url, page) is None:
                    page_move.fix_url(page, user, name)
                    continue

                user_params = {
                    "action": "query",
                    "list": "users",
                    "ususers": user,
                    "format": "json"
                }

                # guild = self.bot.get_guild(697848129185120256)
                # role = guild.get_role(843007895573889024)
                user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
                user_json = user_request.json()
                user_id = str(user_json['query']['users'][0]['userid'])

                threads.update(channel.threads)
                async for thread in channel.archived_threads():
                    threads.add(thread)
                thread = discord.utils.get(threads, name='Draft: ' + name)

                draft_url = self.db.get_draft(page).url if self.db.get_draft(page) else None
                if not draft_url:
                    continue
                # if no thread for this draft is found:
                if thread is None:
                    embed = discord.Embed(
                        title='Draft: ' + name,
                        url=draft_url,
                        color=discord.Color.from_rgb(36, 255, 0)
                    )
                    embed.set_author(
                        name=user,
                        url=f"https://2b2t.miraheze.org/wiki/User:{user.replace(' ', '_')}",
                        icon_url=f"https://static.miraheze.org/2b2twiki/avatars/2b2twiki_{user_id}_l.png"
                    )

                    draft_message = await channel.send(embed=embed)
                    new_thread = await channel.create_thread(
                        name='Draft: ' + name,
                        message=draft_message,
                        reason="New draft"
                    )
                    threads.add(new_thread)
                    print(f"Found Draft:{user}/{name} at {datetime.datetime.now()}, new thread opened")
                # else if a thread is found but it is closed:
                elif thread.archived:
                    await thread.unarchive()
                    print(f"Found Draft:{user}/{name} at {datetime.datetime.now()}, opened existing thread")
                else:
                    print(f"Found Draft:{user}/{name} at {datetime.datetime.now()}, thread already exists")

        except requests.HTTPError as e:
            print(e)

    @fetch_draft.before_loop
    async def before_fetch_draft(self):
        print('waiting...')
        await self.bot.wait_until_ready()

    @discord.slash_command(name='help', description="Displays and explains this bot's functions")
    async def help(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        embed = discord.Embed(title="Commands",
                              description="Note: for parameters containing spaces, surround the parameters in quotes, or substitute spaces with underscores.",
                              color=0x24ff00)
        embed.add_field(name="List drafts awaiting review", value="/list", inline=False)
        embed.add_field(name="Vote on a draft", value="/vote <user> <article> <duration> <auto>", inline=False)
        # embed.add_field(name="Approve a draft", value='/approve <user> <article> <"category 1, category 2, etc.">', inline=False)
        # embed.add_field(name="Reject a draft", value='/reject <user> <article> <"reason">', inline=False)
        await ctx.respond(embed=embed)

    async def approve(self, user, name, categories):
        datetime_object = datetime.datetime.now()
        print(f"Command /approve {user} {name} run at {str(datetime_object)}")
        draft_deny.deny_page(user, name, "Approved draft")
        clean_redirects.clean(user, name)
        if categories is not None:
            add_category.add_category(user, name, categories)
        draft_move.move_page(user, name)
        self.db.remove_draft(f"User:{user}/Drafts/{name}")
        thread = discord.utils.get(threads, name='Draft: ' + name)
        await thread.archive()
        user = user.replace(" ", "_")
        name = name.replace(" ", "_")
        print(f"Successfully moved page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}> to page " +
              f"<https://2b2t.miraheze.org/wiki/{name}>")

    async def reject(self, user, name, summary):
        datetime_object = datetime.datetime.now()
        print(f"Command /reject {user} {name} {summary} run at {str(datetime_object)}")
        if summary is None:
            summary = "Rejected draft"
        draft_deny.deny_page(user, name, summary)
        self.db.remove_draft(f"User:{user}/Drafts/{name}")
        thread = discord.utils.get(threads, name='Draft: ' + name)
        await thread.archive()
        user = user.replace(" ", "_")
        name = name.replace(" ", "_")
        print(f"Successfully rejected page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}>")

    @discord.slash_command(name='list', description="Provides a list of all pending drafts")
    async def list(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        master_list = []
        pages = []
        master_list.append(pages)
        counter = 0
        
        drafts = self.db.get_all_drafts()
        for page, draft in drafts.items():
            name = page[page.find('/', page.find('/') + 1) + 1:]
            user = page[page.find(':') + 1:page.find('/')]
            
            user_params = {
                "action": "query",
                "list": "users",
                "ususers": user,
                "format": "json"
            }
            user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
            user_json = user_request.json()
            user_id = str(user_json['query']['users'][0]['userid'])
            
            embed = discord.Embed(
                title='Draft: ' + name,
                url=draft.url,
                color=discord.Color.from_rgb(36, 255, 0)
            )
            embed.set_author(
                name=user,
                url=f"https://2b2t.miraheze.org/wiki/User:{user.replace(' ', '_')}",
                icon_url=f"https://static.miraheze.org/2b2twiki/avatars/2b2twiki_{user_id}_l.png"
            )
            
            if len(master_list[counter]) < 10:
                master_list[counter].append(embed)
            else:
                counter += 1
                new_list = []
                master_list.append(new_list)
                master_list[counter].append(embed)
                
        for page_list in master_list:
            await ctx.respond(embeds=page_list)

    @discord.slash_command(name='debug', description='Intended for bot developers only')
    @commands.has_role(1159901879417974795)
    async def debug(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        master_list = []
        pages = []
        master_list.append(pages)
        counter = 0
        
        drafts = self.db.get_all_drafts()
        for page in drafts:
            embed = discord.Embed(title=page)
            if len(master_list[counter]) < 10:
                master_list[counter].append(embed)
            else:
                counter += 1
                new_list = []
                master_list.append(new_list)
                master_list[counter].append(embed)
                
        for page_list in master_list:
            await ctx.respond(embeds=page_list, ephemeral=True)
    
    @discord.slash_command(name='dbcheck', description='Check database status')
    @commands.has_role(1159901879417974795)  # Bot Wrangler role
    async def dbcheck(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        
        try:
            # Check if database file exists
            if not path.exists(self.db.db_path):
                await ctx.respond(f"Database file not found at: {self.db.db_path}", ephemeral=True)
                return
                
            # Get all drafts
            drafts = self.db.get_all_drafts()
            
            # Create debug info embed
            embed = discord.Embed(
                title="Database Status",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Database Path", 
                value=self.db.db_path, 
                inline=False
            )
            
            embed.add_field(
                name="Number of Drafts", 
                value=str(len(drafts)), 
                inline=False
            )
            
            if drafts:
                # Show first few drafts as sample
                sample = list(drafts.items())[:5]
                sample_text = "\n".join(f"- {title}" for title, _ in sample)
                if len(drafts) > 5:
                    sample_text += "\n..."
                
                embed.add_field(
                    name="Sample Drafts",
                    value=sample_text or "None",
                    inline=False
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"Error checking database: {str(e)}", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(DraftBot(bot))