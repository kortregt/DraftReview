import asyncio

import discord
from discord.ext import commands


class Poll(discord.ui.View):
    yesList = []
    noList = []

    @discord.ui.button(label="Approve: 0", custom_id="approve", style=discord.ButtonStyle.green, emoji="👍")
    async def approve_callback(self, approve, interaction: discord.Interaction):
        user = interaction.user
        if user not in self.yesList:
            self.yesList.append(user)
            if user in self.noList:
                self.noList.remove(user)
                self.children[1].label = f"Reject: {len(self.noList)}"
        else:
            self.yesList.remove(user)
        approve.label = f"Approve: {len(self.yesList)}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Reject: 0", custom_id="reject", style=discord.ButtonStyle.red, emoji="👎")
    async def reject_callback(self, reject, interaction: discord.Interaction):
        user = interaction.user
        if user not in self.noList:
            self.noList.append(user)
            if user in self.yesList:
                self.yesList.remove(user)
                self.children[0].label = f"Approve: {len(self.yesList)}"
        else:
            self.noList.remove(user)
        reject.label = f"Reject: {len(self.noList)}"
        await interaction.response.edit_message(view=self)


class DraftVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_id = 0

    @discord.application_command(name="vote", description="Starts/ends voting on a draft.")
    @commands.has_role(843007895573889024)
    @discord.option("duration", float, description="Length of the vote in hours", required=False)
    @discord.option("name", str, description="Author of the draft", required=True)
    @discord.option("title", str, description="Title of the draft", required=True)
    async def vote(self, interaction: discord.Interaction, name, title, duration):
        await interaction.response.defer()
        page = discord.Embed(title=f"Vote for Draft: {title} by {name}",
                             color=discord.Color.from_rgb(36, 255, 0))
        poll = Poll()
        message = await interaction.followup.send(embed=page, view=poll)
        # await asyncio.sleep(5)  # testing purposes
        if duration is not None:
            await asyncio.sleep(duration*3600)
        else:
            await asyncio.sleep(86400)  # one day
        poll.children[0].disabled = True
        poll.children[1].disabled = True
        page.title = f"Vote for Draft: {title} by {name} has ended"
        await message.edit(embed=page, view=poll)


def setup(bot):
    bot.add_cog(DraftVote(bot))
