import discord
import requests
from discord.ext import tasks, commands
import datetime
import re

import draft_deny
import draft_move
import page_move
import clean_redirects
import add_category

good_url = re.compile('.+Drafts/.+')

threads = set()


def populate_dic():
    pageDic = {}
    params = {"action": "query", "list": "categorymembers", "cmtitle": "Category:Drafts_awaiting_review",
              "format": "json"}
    url = 'https://2b2t.miraheze.org/'

    request = requests.get(url + "w/api.php", params=params)
    request.raise_for_status()
    json_data = request.json()

    pages = json_data['query']['categorymembers']
    for i in range(len(pages)):
        title = pages[i]['title']
        link = url + "wiki/" + pages[i]['title']
        link = link.replace(" ", "_")
        pageDic[title] = link
    return pageDic


class DraftBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.draft_dict = {}
        self.fetch_draft.start()

    def cog_unload(self):
        self.fetch_draft.cancel()

    @tasks.loop(seconds=60)
    async def fetch_draft(self, *args):
        # channel = self.bot.get_channel(1075585762243915787)  # channel ID goes here (bot testing)
        channel = self.bot.get_channel(842662513400348684)  # channel ID goes here (draft-review)

        oldReviewPages = set(self.draft_dict)
        try:
            self.draft_dict = populate_dic()
            newReviewPages = set(self.draft_dict)
            newPages = [x for x in newReviewPages if x not in oldReviewPages]
            for page in newPages:
                name = page[page.find('/', page.find('/') + 1) + 1:]
                user = page[page.find(':') + 1:page.find('/')]
                if re.fullmatch(good_url, page) is None:
                    page_move.fix_url(page, user, name)
                    continue
                user_params = {"action": "query", "list": "users", "ususers": page[page.find(':') + 1:page.find('/')],
                               "format": "json"}
                user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
                user_json = user_request.json()
                user_id = str(user_json['query']['users'][0]['userid'])

                guild = self.bot.get_guild(697848129185120256)
                role = guild.get_role(843007895573889024)
                threads.update(channel.threads)
                async for thread in channel.archived_threads():
                    threads.add(thread)
                thread = discord.utils.get(threads, name='Draft: ' + name)
                # if no thread for this draft is found:
                if thread is None:
                    embed = discord.Embed(title='Draft: ' + name, url=self.draft_dict[page],
                                          color=discord.Color.from_rgb(36, 255, 0))
                    embed.set_author(name=user, url="https://2b2t.miraheze.org/wiki/User:" + user.replace(" ", "_"),
                                     icon_url="https://static.miraheze.org/2b2twiki/avatars/2b2twiki_" + user_id +
                                              "_l.png")

                    # await channel.send(role.mention, embed=embed)  # ping
                    draft_message = await channel.send(embed=embed)  # no ping
                    new_thread = await channel.create_thread(name='Draft: ' + name, message=draft_message,
                                                             reason="New draft")
                    threads.add(new_thread)
                    datetime_object = datetime.datetime.now()
                    print(f"Found Draft:{user}/{name} at {str(datetime_object)}, new thread opened")
                # else if a thread is found but it is closed:
                elif thread.archived:
                    await thread.unarchive()
                    datetime_object = datetime.datetime.now()
                    print(f"Found Draft:{user}/{name} at {str(datetime_object)}, opened existing thread")
                else:
                    datetime_object = datetime.datetime.now()
                    print(f"Found Draft:{user}/{name} at {str(datetime_object)}, thread already exists")
        except requests.HTTPError as e:
            print(e)

    @fetch_draft.before_loop
    async def before_fetch_draft(self):
        print('waiting...')
        await self.bot.wait_until_ready()

    @commands.command(name='help')
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(title="Commands",
                              description="Note: for parameters containing spaces, surround the parameters in quotes, "
                                          "or substite spaces with underscores.", color=0x24ff00)
        embed.add_field(name="Vote on a draft", value="~vote <start|end> <user> <article>", inline=False)
        embed.add_field(name="Approve a draft", value='~approve <user> <article> <"category 1, category 2, etc.">',
                        inline=False)
        embed.add_field(name="Reject a draft", value='~reject <user> <article> <"reason">', inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='approve')
    async def approve(self, ctx: commands.Context, user, name, categories=None):
        datetime_object = datetime.datetime.now()
        print(f"Command ~approve {user} {name} run at {str(datetime_object)}")
        draft_deny.deny_page(user, name, "Approved draft")
        clean_redirects.clean(user, name)
        if categories is not None:
            add_category.add_category(user, name, categories)
        draft_move.move_page(user, name)
        user = user.replace(" ", "_")
        name = name.replace(" ", "_")
        await ctx.send(f"Successfully moved page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}> to page " +
                       f"<https://2b2t.miraheze.org/wiki/{name}>")
        print(f"Successfully moved page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}> to page " +
              f"<https://2b2t.miraheze.org/wiki/{name}>")
        del self.draft_dict[f"User:{user}/Drafts/{name}"]
        thread = discord.utils.get(threads, name='Draft: ' + name)
        await thread.archive()

    @commands.command(name='reject')
    async def reject(self, ctx: commands.Context, user, name, summary='Rejected draft'):
        datetime_object = datetime.datetime.now()
        print(f"Command ~reject {user} {name} {summary} run at {str(datetime_object)}")
        draft_deny.deny_page(user, name, summary)
        user = user.replace(" ", "_")
        name = name.replace(" ", "_")
        await ctx.send(f"Successfully rejected page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}>")
        print(f"Successfully rejected page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}>")
        del self.draft_dict[f"User:{user}/Drafts/{name}"]
        thread = discord.utils.get(threads, name='Draft: ' + name)
        await thread.archive()


def setup(bot: commands.Bot):
    bot.add_cog(DraftBot(bot))
