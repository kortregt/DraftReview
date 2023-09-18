import asyncio
import time

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
        await interaction.response.edit_message(view=self) # change edit_messages to followups.

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
        await interaction.response.edit_message(view=self) # change edit_messages to followups.

"""
Message that sends the button to view the Modal.
"""
class ModalMessage(discord.ui.View):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title = ""
        self.accepted = False
        self.draftName = ""
        self.draftTitle = ""

    @discord.ui.button(label="Give input for Draft", style=discord.ButtonStyle.green)
    async def button_callback(self, button, interaction: discord.Interaction):
        modal = VoteModal(title=self.title) # Object within and Object. Objectception.
        modal.draftName = self.draftName # gotta parse this shit through
        modal.draftTitle = self.draftTitle

        if self.accepted:
            modal.accepted = True
            modal.add_item(discord.ui.InputText(label="Categories for Draft"))
        else:
            modal.add_item(discord.ui.InputText(label="Reason for Rejection"))

        await interaction.response.send_modal(modal)


class DraftVote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vote_id = 0

    async def sendModal(self, interaction: discord.Interaction, poll: Poll, name, title):
        # TODO: Parse the poll draft title and author through.
        modal = ModalMessage()
        modal.draftName = name
        modal.draftTitle = title

        if len(poll.yesList) >= len(poll.noList): # Not sure on rules here, will need to deliberate.
            modal.title = "Accepted"
            modal.accepted = True
            await interaction.followup.send(view=modal, ephemeral=True)
        else:
            modal.title = "Rejected"
            await interaction.followup.send(view=modal, ephemeral=True)

        

    @discord.commands.application_command(name="vote", description="Starts/ends voting on a draft.")
    #@commands.has_role(843007895573889024)
    @discord.option("duration", float, description="Length of the vote in hours", required=False)
    @discord.option("name", str, description="Author of the draft", required=True)
    @discord.option("title", str, description="Title of the draft", required=True)
    async def vote(self, interaction: discord.Interaction, name, title, duration=24):
        await interaction.response.defer()
        page = discord.Embed(title=f"Vote for Draft: {title} by {name}",
                             color=discord.Color.from_rgb(36, 255, 0),
                             description=("Vote end: <t:" + str(round(time.time()+duration*3600))) + ":R>")
        
        poll = Poll() # Create Poll object
        message = await interaction.followup.send(embed=page, view=poll) # Parse Poll and embed onto a message, and send it.
        # await asyncio.sleep(5)  # testing purposes
        await asyncio.sleep(duration*3600) # duration parsed through
        poll.children[0].disabled = True # Disable both buttons. Luckily, they are the only children.
        poll.children[1].disabled = True
        page.title = f"Vote for Draft: {title} by {name} has ended"
        # TODO: If we want to have the one who started the poll pinged, we will need to do this differenty.
        #guild = self.bot.get_guild(697848129185120256) # get role from discord server
        #role = guild.get_role(843007895573889024)
        await message.edit(embed=page, view=poll) # edit the poll with the buttons disabled.

        #await interaction.followup.send(role.mention, allowed_mentions=discord.AllowedMentions.all()) # send a mention to the role.
        
        # TODO: instead of a mention to the role, send a MODAL depending on Rejected / Accepted.
        await self.sendModal(interaction, poll, name, title)

"""
Create Modal for user interaction after vote completion
"""
class VoteModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.accepted = False # Defaulted to false, changed to True in ModalMesage() class.
        self.draftName = ""
        self.draftTitle = ""

    async def callback(self, interaction: discord.Interaction):
        textInput = self.children[0].value # this is what the user has inputted into the textbox.
        if self.accepted:
            # TODO: what to do if the Modal is an accepted Modal
            print("ACCEPTED {0} by {1}".format(self.draftName, self.draftTitle))
        else:
            # TODO: what to do if the Modal is a rejected Modal.
            print("REJECTED {0} by {1}".format(self.draftName, self.draftTitle))


        #embed = discord.Embed(title="Modal Results")
        #embed.add_field(name="Short Input", value=self.children[0].value)
        #embed.add_field(name="Long Input", value=self.children[1].value)
        #await interaction.response.send_message(embeds=[embed])


def setup(bot):
    bot.add_cog(DraftVote(bot))
