import asyncio
import os
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

import discord
from discord import Poll, PollMedia, PollAnswer
from discord.ext import commands
from discord.ui import Modal, InputText, View, Button

from draft_database import DraftDatabase

# Set up logger
logger = logging.getLogger(__name__)


@dataclass
class ActiveVote:
    """Tracks an active poll vote."""
    message_id: int
    channel_id: int
    author: str
    draft_name: str
    draft_url: str
    required_votes: int
    duration_hours: float
    end_time: int
    approve_count: int = 0
    reject_count: int = 0
    result: Optional[str] = None  # "approve", "reject", "tie", or None
    completed: asyncio.Event = None

    def __post_init__(self):
        if self.completed is None:
            self.completed = asyncio.Event()


def log_vote(message: str) -> None:
    """Log vote events to a file."""
    log_dir = os.getenv('LOG_DIR', '/app/logs')
    log_file_path = os.path.join(log_dir, 'votes.log')
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file_path, 'a') as file:
        file.write(f"[{timestamp}] {message}\n")


def validate_duration(duration_hours: float) -> tuple[float, Optional[str]]:
    """Validate and cap duration at 32 hours per user requirements."""
    MAX_DURATION = 32  # 32 hours as specified by user

    if duration_hours <= 0:
        return 24.0, "⚠️ Duration must be positive. Using default 24 hours."

    if duration_hours > MAX_DURATION:
        return MAX_DURATION, f"⚠️ Duration capped at {MAX_DURATION} hours (maximum allowed)."

    return duration_hours, None


class ReviewModal(Modal):
    def __init__(self, is_approval: bool) -> None:
        title = "Draft Review" if is_approval else "Draft Rejection"
        super().__init__(title=title)

        self.input = InputText(
            label="Categories" if is_approval else "Rejection Reason",
            placeholder=("Enter categories separated by commas" if is_approval
                         else "Enter reason for rejection"),
            style=discord.InputTextStyle.paragraph,
            required=True,
            row=0
        )
        self.add_item(self.input)
        self.result = None

    async def callback(self, interaction: discord.Interaction):
        self.result = self.input.value
        await interaction.response.defer()


def create_poll(draft_name: str, author: str, duration_hours: float) -> Poll:
    """Create a Discord poll object."""
    question = PollMedia(text=f"Vote: {draft_name} by {author}")
    answers = [
        PollAnswer(text="Approve", emoji="✅"),
        PollAnswer(text="Reject", emoji="❌")
    ]
    duration = int(duration_hours)
    return Poll(
        question=question,
        answers=answers,
        duration=duration,
        allow_multiselect=False
    )


def create_status_embed(draft_name: str, author: str, draft_url: str,
                       required_votes: int, duration_hours: float, end_time: int) -> discord.Embed:
    """Create embed with vote context."""
    embed = discord.Embed(
        title=f"📊 Vote: {draft_name}",
        description=(
            f"**Author:** {author}\n"
            f"**Draft:** [View Draft]({draft_url})\n\n"
            f"**Required votes:** {required_votes}\n"
            f"**Duration:** {duration_hours} hours\n"
            f"**Ends:** <t:{end_time}:R>\n\n"
            f"Vote using the poll below. "
            f"First option to reach {required_votes} votes wins."
        ),
        color=discord.Color.blue()
    )
    return embed


class FinalizeView(View):
    """View with button to trigger ReviewModal for finalizing vote."""

    def __init__(self, is_approval: bool):
        super().__init__(timeout=300)  # 5 minutes to respond
        self.is_approval = is_approval
        self.result = None

        # Add the button dynamically based on approval status
        button = Button(
            label="Add Categories" if is_approval else "Add Rejection Reason",
            style=discord.ButtonStyle.primary,
            emoji="📝"
        )
        button.callback = self.finalize
        self.add_item(button)

    async def finalize(self, interaction: discord.Interaction):
        """Show modal to collect categories or rejection reason."""
        modal = ReviewModal(self.is_approval)
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.result = modal.result
        self.stop()


class DraftVote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        db_path = os.getenv('DATABASE_PATH')
        self.db = DraftDatabase(db_path)
        self.active_votes: Dict[int, ActiveVote] = {}  # message_id -> ActiveVote

    @commands.Cog.listener()
    async def on_raw_poll_vote_add(self, payload):
        """Handle poll votes and check for threshold."""
        vote = self.active_votes.get(payload.message_id)
        if not vote:
            return  # Not one of our tracked polls

        try:
            # Fetch the message to get updated poll results
            channel = self.bot.get_channel(vote.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(vote.message_id)
            poll = message.poll

            if not poll or not poll.results:
                return

            answer_counts = poll.results.answer_counts
            if len(answer_counts) < 2:
                return

            # Update vote counts
            vote.approve_count = answer_counts[0].count
            vote.reject_count = answer_counts[1].count

            # Check if threshold reached
            approve_threshold = vote.approve_count >= vote.required_votes
            reject_threshold = vote.reject_count >= vote.required_votes

            if approve_threshold and reject_threshold:
                # Both reached threshold - determine winner
                if vote.approve_count > vote.reject_count:
                    vote.result = "approve"
                elif vote.reject_count > vote.approve_count:
                    vote.result = "reject"
                else:
                    vote.result = "tie"

                log_vote(f"Poll threshold reached for {vote.draft_name}: "
                        f"{vote.result.upper()} ({vote.approve_count} approve, "
                        f"{vote.reject_count} reject)")
                vote.completed.set()

            elif approve_threshold:
                vote.result = "approve"
                log_vote(f"Poll threshold reached for {vote.draft_name}: "
                        f"APPROVE ({vote.approve_count} votes)")
                vote.completed.set()

            elif reject_threshold:
                vote.result = "reject"
                log_vote(f"Poll threshold reached for {vote.draft_name}: "
                        f"REJECT ({vote.reject_count} votes)")
                vote.completed.set()

        except discord.HTTPException as e:
            logger.error(f"Failed to fetch poll results for {vote.draft_name}: {e}")

    async def wait_for_vote_completion(self, vote: ActiveVote) -> Optional[str]:
        """Wait for vote to complete via threshold or timeout."""
        duration_seconds = vote.duration_hours * 3600

        try:
            await asyncio.wait_for(vote.completed.wait(), timeout=duration_seconds)
            return vote.result
        except asyncio.TimeoutError:
            # Timeout reached
            log_vote(f"Poll timed out for {vote.draft_name}: "
                    f"{vote.approve_count} approve, {vote.reject_count} reject "
                    f"(needed {vote.required_votes})")
            return None
        finally:
            # Clean up active vote
            self.active_votes.pop(vote.message_id, None)

    @discord.slash_command(
        name="vote",
        description="Start a vote on a draft using Discord polls"
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
        Start a poll vote on a draft

        Parameters
        ----------
        author : str
            The author of the draft
        draft_name : str
            The name of the draft
        required_votes : int
            Number of votes required for decision (default: 3)
        duration : float
            Duration of vote in hours (default: 24, max: 32)
        """
        await ctx.defer()

        try:
            # Verify draft exists
            draft_title = f"User:{author}/Drafts/{draft_name}"
            draft = self.db.get_draft(draft_title)
            if not draft:
                await ctx.followup.send(
                    f"❌ Error: Draft '{draft_name}' by {author} not found.",
                    ephemeral=True
                )
                return

            # Validate and cap duration
            duration, warning = validate_duration(duration)
            if warning:
                await ctx.followup.send(warning, ephemeral=True)

            # Calculate end time
            end_time = int((datetime.now() + timedelta(hours=duration)).timestamp())

            # Create poll and embed
            poll = create_poll(draft_name, author, duration)
            embed = create_status_embed(draft_name, author, draft.url, required_votes, duration, end_time)

            # Send poll
            message = await ctx.followup.send(embed=embed, poll=poll)

            # Create and track active vote
            vote = ActiveVote(
                message_id=message.id,
                channel_id=ctx.channel_id,
                author=author,
                draft_name=draft_name,
                draft_url=draft.url,
                required_votes=required_votes,
                duration_hours=duration,
                end_time=end_time
            )
            self.active_votes[message.id] = vote

            log_vote(f"Poll vote started for {draft_name} by {author} - "
                    f"required: {required_votes}, duration: {duration}h")

            # Wait for completion via events or timeout
            result = await self.wait_for_vote_completion(vote)

            # Handle timeout
            if result is None:
                timeout_embed = discord.Embed(
                    title="⏱️ Vote Timed Out",
                    description=(
                        f"Vote for **{draft_name}** by {author} has timed out.\n\n"
                        f"Final tally:\n"
                        f"✅ Approve: {vote.approve_count}\n"
                        f"❌ Reject: {vote.reject_count}\n\n"
                        f"Required votes: {required_votes}\n"
                        f"No action taken."
                    ),
                    color=discord.Color.orange()
                )
                await ctx.followup.send(embed=timeout_embed)
                return

            # Handle tie
            if result == "tie":
                tie_embed = discord.Embed(
                    title="🤝 Vote Tied",
                    description=(
                        f"Vote for **{draft_name}** by {author} ended in a tie.\n\n"
                        f"Final tally: {vote.approve_count}-{vote.reject_count}\n\n"
                        f"No action taken. Start a new vote if needed."
                    ),
                    color=discord.Color.gold()
                )
                await ctx.followup.send(embed=tie_embed)
                log_vote(f"Vote tied for {draft_name} by {author}")
                return

            # Re-validate draft still exists before finalizing
            draft = self.db.get_draft(draft_title)
            if not draft:
                await ctx.followup.send(
                    f"⚠️ Draft '{draft_name}' no longer exists. Vote cancelled.",
                    ephemeral=True
                )
                return

            # Show finalization button to collect categories/reason
            is_approval = (result == "approve")
            finalize_view = FinalizeView(is_approval=is_approval)

            finalize_prompt = await ctx.followup.send(
                f"{'✅ **Vote Approved**' if is_approval else '❌ **Vote Rejected**'}\n\n"
                f"**{draft_name}** by {author}\n"
                f"Final tally: {vote.approve_count} approve, {vote.reject_count} reject\n\n"
                f"Click the button below to finalize:",
                view=finalize_view,
                ephemeral=True
            )

            # Wait for modal completion (5 minute timeout)
            await finalize_view.wait()

            if finalize_view.result is None:
                await ctx.followup.send(
                    "⚠️ Finalization timed out. No action taken.",
                    ephemeral=True
                )
                return

            # Execute approval or rejection
            if is_approval:
                await self.bot.get_cog('DraftBot').approve(
                    author, draft_name, finalize_view.result
                )
                result_embed = discord.Embed(
                    title="✅ Draft Approved",
                    description=(
                        f"**{draft_name}** by {author} has been approved.\n\n"
                        f"Categories: {finalize_view.result}\n"
                        f"Final vote: {vote.approve_count} approve, "
                        f"{vote.reject_count} reject"
                    ),
                    color=discord.Color.green()
                )
            else:
                await self.bot.get_cog('DraftBot').reject(
                    author, draft_name, finalize_view.result
                )
                result_embed = discord.Embed(
                    title="❌ Draft Rejected",
                    description=(
                        f"**{draft_name}** by {author} has been rejected.\n\n"
                        f"Reason: {finalize_view.result}\n"
                        f"Final vote: {vote.approve_count} approve, "
                        f"{vote.reject_count} reject"
                    ),
                    color=discord.Color.red()
                )

            await ctx.followup.send(embed=result_embed)
            log_vote(f"Vote completed for {draft_name} by {author}: "
                    f"{'Approved' if is_approval else 'Rejected'} - "
                    f"{finalize_view.result}")

        except Exception as e:
            logger.error(f"Error in vote command: {str(e)}", exc_info=True)
            log_vote(f"Vote error for {draft_name} by {author}: {str(e)}")
            await ctx.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


def setup(bot: commands.Bot):
    bot.add_cog(DraftVote(bot))