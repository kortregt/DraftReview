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

def get_user_id(username: str) -> str:
    """Get user ID from MediaWiki API."""
    user_params = {
        "action": "query",
        "list": "users",
        "ususers": username,
        "format": "json"
    }
    user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
    user_json = user_request.json()
    return str(user_json['query']['users'][0]['userid'])

def get_user_ids(usernames: list[str]) -> dict[str, str]:
    """Get multiple user IDs in a single API call."""
    if not usernames:
        return {}
        
    user_params = {
        "action": "query",
        "list": "users",
        "ususers": "|".join(usernames),
        "format": "json"
    }
    user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
    user_json = user_request.json()
    return {user_info['name']: str(user_info['userid']) 
            for user_info in user_json['query']['users']}

def populate_db(db: DraftDatabase):
    """Populate the database with drafts from the wiki API."""
    headers = {
        'User-Agent': '2b2tWikiBot/2.0 (Miraheze; 2b2t Wiki) Draft Review Bot'
    }
    
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Drafts_awaiting_review",
        "cmlimit": "100",
        "format": "json"
    }

    url = 'https://2b2t.miraheze.org/w/api.php'
    
    try:
        print("=== DEBUG: Making API request ===")
        request = requests.get(url, params=params, headers=headers)
        request.raise_for_status()
        
        print(f"=== DEBUG: API Response Status: {request.status_code} ===")
        print(f"=== DEBUG: API Response Headers: {dict(request.headers)} ===")
        print(f"=== DEBUG: API Response Content: {request.text[:200]}... ===")
        
        json_data = request.json()
        
        if 'query' not in json_data:
            print(f"Error: 'query' not found in response. Full response: {json_data}")
            return
            
        if 'categorymembers' not in json_data['query']:
            print(f"Error: 'categorymembers' not found in query. Full response: {json_data}")
            return

        pages = json_data['query']['categorymembers']
        for page in pages:
            title = page['title']
            link = f"https://2b2t.miraheze.org/wiki/{title.replace(' ', '_')}"
            db.add_draft(title, link)
            
            # Extract username from title and update user cache if needed
            username = title[title.find(':') + 1:title.find('/')]
            cache_age = db.get_user_cache_age(username)
            if cache_age is None or cache_age > 86400:  # Cache for 24 hours
                try:
                    user_id = get_user_id(username)
                    db.add_user(username, user_id)
                    print(f"Updated user cache for {username}")
                except Exception as e:
                    print(f"Failed to get user ID for {username}: {e}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request error in populate_db: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        raise
    except ValueError as e:
        print(f"JSON parsing error in populate_db: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error in populate_db: {str(e)}")
        raise


class DraftBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        db_path = os.getenv('DATABASE_PATH')
        self.db = DraftDatabase(db_path)
        
        # Initial population and caching
        print("=== Performing initial database population and user caching ===")
        populate_db(self.db)
        
        # Cache all users from existing drafts
        drafts = self.db.get_all_drafts()
        users_to_cache = set()
        for title in drafts.keys():
            username = title[title.find(':') + 1:title.find('/')]
            cache_age = self.db.get_user_cache_age(username)
            if cache_age is None or cache_age > 86400:  # Cache for 24 hours
                users_to_cache.add(username)
        
        if users_to_cache:
            print(f"=== Caching {len(users_to_cache)} users ===")
            try:
                user_ids = get_user_ids(list(users_to_cache))
                for username, user_id in user_ids.items():
                    self.db.add_user(username, user_id)
                    print(f"Cached user ID for {username}")
            except Exception as e:
                print(f"Error caching user IDs: {e}")
        
        self.fetch_draft.start()

    def cog_unload(self):
        self.fetch_draft.cancel()

    @tasks.loop(seconds=60)
    async def fetch_draft(self, *args):
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
                    
                    # Get user ID from cache
                    user_data = self.db.get_user(user)
                    if user_data:
                        embed.set_author(
                            name=user,
                            url=f"https://2b2t.miraheze.org/wiki/User:{user.replace(' ', '_')}",
                            icon_url=f"https://static.miraheze.org/2b2twiki/avatars/2b2twiki_{user_data.user_id}_l.png"
                        )
                    else:
                        embed.set_author(
                            name=user,
                            url=f"https://2b2t.miraheze.org/wiki/User:{user.replace(' ', '_')}"
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
        try:
            drafts = self.db.get_all_drafts()
            if not drafts:
                await ctx.respond("No drafts found.")
                return

            # Create embeds
            master_list = []
            pages = []
            master_list.append(pages)
            counter = 0

            # Create embeds
            for page, draft in drafts.items():
                name = page[page.find('/', page.find('/') + 1) + 1:]
                user = page[page.find(':') + 1:page.find('/')]

                embed = discord.Embed(
                    title='Draft: ' + name,
                    url=draft.url,
                    color=discord.Color.from_rgb(36, 255, 0)
                )
                
                # Get user ID from cache
                user_data = self.db.get_user(user)
                if user_data:
                    embed.set_author(
                        name=user,
                        url=f"https://2b2t.miraheze.org/wiki/User:{user.replace(' ', '_')}",
                        icon_url=f"https://static.miraheze.org/2b2twiki/avatars/2b2twiki_{user_data.user_id}_l.png"
                    )
                else:
                    embed.set_author(
                        name=user,
                        url=f"https://2b2t.miraheze.org/wiki/User:{user.replace(' ', '_')}"
                    )

                if len(master_list[counter]) < 10:
                    master_list[counter].append(embed)
                else:
                    counter += 1
                    new_list = []
                    master_list.append(new_list)
                    master_list[counter].append(embed)

            # Send all embeds in a single response
            await ctx.respond(embeds=master_list[0])
            for page_list in master_list[1:]:
                if page_list:  # Only send if there are embeds
                    await ctx.followup.send(embeds=page_list)

        except Exception as e:
            await ctx.respond(f"Error listing drafts: {str(e)}")

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
                
            # Get all drafts and users
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
            
            # Add user cache info
            users = set()
            for title in drafts.keys():
                username = title[title.find(':') + 1:title.find('/')]
                users.add(username)
            
            cached_users = []
            for username in users:
                user_data = self.db.get_user(username)
                if user_data:
                    cached_users.append(username)
            
            embed.add_field(
                name="User Cache Status",
                value=f"Cached {len(cached_users)} out of {len(users)} users",
                inline=False
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"Error checking database: {str(e)}", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(DraftBot(bot))
