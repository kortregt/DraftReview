import asyncio
import time
import os
from typing import Optional, List
from datetime import datetime, timedelta
import logging

import discord
from discord.ext import commands
from discord import ButtonStyle

from draft_database import DraftDatabase

# Set up logger
logger = logging.getLogger(__name__)


def log_vote(message: str) -> None:
    """Log vote events to a file."""
    log_dir = os.getenv('LOG_DIR', '/app/logs')
    log_file_path = os.path.join(log_dir, 'votes.log')
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file_path, 'a') as file:
        file.write(f"[{timestamp}] {message}\n")


class ReviewModal(discord.Modal):
    def __init__(self, is_approval: bool) -> None:
        title = "Draft Review" if is_approval else "Draft Rejection"
        super().__init__(title=title)

        self.input = discord.TextInput(
            label="Categories" if is_approval else "Rejection Reason",
            placeholder=("Enter categories separated by commas" if is_approval
                         else "Enter reason for rejection"),
            style=discord.TextStyle.paragraph,
            required=True,
            row=0
        )
        self.add_item(self.input)
        self.result = None

    async def callback(self, interaction: discord.Interaction):
        self.result = self.input.value
        await interaction.response.defer()


class VoteView(discord.ui.View):
    def __init__(self,
                 author: str,
                 draft_name: str,
                 required_votes: int = 3,
                 timeout: float = 86400):  # 24 hours default
        super().__init__(timeout=timeout)
        self.author = author
        self.draft_name = draft_name
        self.required_votes = required_votes
        self.approve_votes: List[int] = []
        self.reject_votes: List[int] = []
        self.result: Optional[bool] = None
        self.end_time = int((datetime.now() + timedelta(seconds=timeout)).timestamp())
        self.message = None

    def _create_status_embed(self) -> discord.Embed:
        """Create an embed showing the current voting status."""
        embed = discord.Embed(
            title=f"Vote: {self.draft_name}",
            description=(
                f"Draft by {self.author}\n\n"
                f"Required votes: {self.required_votes}\n"
                f"Ends: <t:{self.end_time}:R>\n\n"
                f"Current status:\n"
                f"✅ Approve: {len(self.approve_votes)}\n"
                f"❌ Reject: {len(self.reject_votes)}"
            ),
            color=discord.Color.blue()
        )
        return embed

    @discord.ui.button(label="Approve (0)", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_vote(interaction, True)

    @discord.ui.button(label="Reject (0)", style=discord.ButtonStyle.red, emoji="❌")
    async def reject(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_vote(interaction, False)

    async def _handle_vote(self, interaction: discord.Interaction, is_approve: bool):
        """Handle a vote being cast."""
        user_id = interaction.user.id

        # Remove existing votes by this user
        if user_id in self.approve_votes:
            self.approve_votes.remove(user_id)
        if user_id in self.reject_votes:
            self.reject_votes.remove(user_id)

        # Add new vote
        if is_approve:
            self.approve_votes.append(user_id)
        else:
            self.reject_votes.append(user_id)

        # Update button labels
        self.children[0].label = f"Approve ({len(self.approve_votes)})"
        self.children[1].label = f"Reject ({len(self.reject_votes)})"

        # Check if we've reached the required votes
        if len(self.approve_votes) >= self.required_votes:
            self.result = True
            self.stop()
        elif len(self.reject_votes) >= self.required_votes:
            self.result = False
            self.stop()

        # Update the message
        embed = self._create_status_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self) -> None:
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)


class DraftVote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        db_path = os.getenv('DRAFT_DB_PATH', 'drafts.db')
        self.db = DraftDatabase(db_path)

    @discord.slash_command(
        name="vote",
        description="Start a vote on a draft"
    )
    @commands.has_any_role(843007895573889024, 1159901879417974795)
    async def vote(
            self,
            ctx: discord.ApplicationContext,
            author: str,
            draft_name: str,
            required_votes: Optional[int] = 3,
            duration: Optional[float] = 24.0
    ):
        """
        Start a vote on a draft

        Parameters
        ----------
        author : str
            The author of the draft
        draft_name : str
            The name of the draft
        required_votes : int
            Number of votes required for decision (default: 3)
        duration : float
            Duration of vote in hours (default: 24)
        """
        await ctx.defer()

        try:
            # Verify draft exists
            draft_title = f"User:{author}/Drafts/{draft_name}"
            draft = self.db.get_draft(draft_title)
            if not draft:
                await ctx.followup.send(
                    f"Error: Draft '{draft_name}' by {author} not found.",
                    ephemeral=True
                )
                return

            # Create and start vote
            view = VoteView(
                author=author,
                draft_name=draft_name,
                required_votes=required_votes,
                timeout=duration * 3600
            )

            embed = view._create_status_embed()
            message = await ctx.followup.send(embed=embed, view=view)
            view.message = message

            log_vote(f"Vote started for {draft_name} by {author}")

            try:
                await view.wait()

                if view.result is None:  # Timeout
                    await ctx.followup.send("Vote has timed out.")
                    return

                # Handle vote result
                modal = ReviewModal(is_approval=view.result)
                await ctx.interaction.response.send_modal(modal)
                await modal.wait()

                if view.result:  # Approved
                    await self.bot.get_cog('DraftBot').approve(author, draft_name, modal.result)
                    result_embed = discord.Embed(
                        title="Draft Approved",
                        description=f"{draft_name} by {author} has been approved.",
                        color=discord.Color.green()
                    )
                else:  # Rejected
                    await self.bot.get_cog('DraftBot').reject(author, draft_name, modal.result)
                    result_embed = discord.Embed(
                        title="Draft Rejected",
                        description=f"{draft_name} by {author} has been rejected.",
                        color=discord.Color.red()
                    )

                await ctx.followup.send(embed=result_embed)
                log_vote(f"Vote completed for {draft_name} by {author}: {'Approved' if view.result else 'Rejected'}")

            except asyncio.TimeoutError:
                log_vote(f"Vote timed out for {draft_name} by {author}")
                await message.edit(content="Vote has timed out.", view=None)
                return

        except Exception as e:
            logger.error(f"Error in vote command: {str(e)}", exc_info=True)
            await ctx.followup.send(f"An error occurred: {str(e)}", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(DraftVote(bot))