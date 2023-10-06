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
              "cmlimit": "100", "format": "json"}
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
        channel = self.bot.get_channel(1150122572294410441)  # channel ID goes here (draft-menders)

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

                # guild = self.bot.get_guild(697848129185120256)
                # role = guild.get_role(843007895573889024)
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

    @discord.application_command(name='help', description="Displays and explains this bot's functions")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="Commands",
                              # description="Note: for parameters containing spaces, surround the parameters in
                              # quotes, " "or substitute spaces with underscores.", color=0x24ff00
                              )
        embed.add_field(name="List drafts awaiting review", value="/list", inline=False)
        embed.add_field(name="Vote on a draft", value="/vote <user> <article> <duration> <auto>", inline=False)
        # embed.add_field(name="Approve a draft", value='/approve <user> <article> <"category 1, category 2, etc.">',
        #                 inline=False)
        # embed.add_field(name="Reject a draft", value='/reject <user> <article> <"reason">', inline=False)
        await interaction.followup.send(embed=embed)

    # @discord.application_command(name='approve', description="Approves a draft on the Wiki")
    # @commands.has_role(843007895573889024)
    # @discord.option("name", str, description="Author of the draft", required=True)
    # @discord.option("title", str, description="Title of the draft", required=True)
    # @discord.option("categories", str, description="Categories to add to the draft. Wrap in quotes and separate "
    #                                                "with commas", required=False)
    async def approve(self, user, name, categories):
        datetime_object = datetime.datetime.now()
        print(f"Command /approve {user} {name} run at {str(datetime_object)}")
        draft_deny.deny_page(user, name, "Approved draft")
        clean_redirects.clean(user, name)
        if categories is not None:
            add_category.add_category(user, name, categories)
        draft_move.move_page(user, name)
        del self.draft_dict[f"User:{user}/Drafts/{name}"]
        user = user.replace(" ", "_")
        name = name.replace(" ", "_")
        print(f"Successfully moved page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}> to page " +
              f"<https://2b2t.miraheze.org/wiki/{name}>")
        thread = discord.utils.get(threads, name='Draft: ' + name)
        await thread.archive()

    # @discord.application_command(name='reject', description="Rejects a draft on the Wiki")
    # @commands.has_role(843007895573889024)
    # @discord.option("name", str, description="Author of the draft", required=True)
    # @discord.option("title", str, description="Title of the draft", required=True)
    # @discord.option("summary", str, description="Reason for rejection, used for the edit summary", required=False)
    async def reject(self, user, name, summary):
        datetime_object = datetime.datetime.now()
        print(f"Command /reject {user} {name} {summary} run at {str(datetime_object)}")
        if summary is None:
            summary = "Rejected draft"
        draft_deny.deny_page(user, name, summary)
        del self.draft_dict[f"User:{user}/Drafts/{name}"]
        user = user.replace(" ", "_")
        name = name.replace(" ", "_")
        print(f"Successfully rejected page <https://2b2t.miraheze.org/wiki/User:{user}/Drafts/{name}>")
        thread = discord.utils.get(threads, name='Draft: ' + name)
        await thread.archive()

    @discord.application_command(name='list', description="Provides a list of all pending drafts")
    async def list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        master_list = []
        pages = []
        master_list.append(pages)
        counter = 0
        for page in self.draft_dict:
            name = page[page.find('/', page.find('/') + 1) + 1:]
            user = page[page.find(':') + 1:page.find('/')]
            user_params = {"action": "query", "list": "users", "ususers": page[page.find(':') + 1:page.find('/')],
                           "format": "json"}
            user_request = requests.get("https://2b2t.miraheze.org/w/api.php", params=user_params)
            user_json = user_request.json()
            user_id = str(user_json['query']['users'][0]['userid'])
            embed = discord.Embed(title='Draft: ' + name, url=self.draft_dict[page],
                                  color=discord.Color.from_rgb(36, 255, 0))
            embed.set_author(name=user, url="https://2b2t.miraheze.org/wiki/User:" + user.replace(" ", "_"),
                             icon_url="https://static.miraheze.org/2b2twiki/avatars/2b2twiki_" + user_id + "_l.png")
            if len(master_list[counter]) < 10:
                master_list[counter].append(embed)
            else:
                counter += 1
                new_list = []
                master_list.append(new_list)
                master_list[counter].append(embed)
        for page_list in master_list:
            await interaction.followup.send(embeds=page_list)

    @discord.application_command(name='debug', description='Intended for bot developers only')
    @commands.has_role(1159901879417974795)
    async def debug(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        master_list = []
        pages = []
        master_list.append(pages)
        counter = 0
        for page in self.draft_dict:
            embed = discord.Embed(title=page)
            if len(master_list[counter]) < 10:
                master_list[counter].append(embed)
            else:
                counter += 1
                new_list = []
                master_list.append(new_list)
                master_list[counter].append(embed)
        for page_list in master_list:
            await interaction.followup.send(embeds=page_list, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(DraftBot(bot))
