import asyncio
import time
import os
from typing import Optional
from datetime import datetime, timedelta
import logging

import discord
from discord import Poll, PollMedia, PollAnswer
from discord.ext import commands
from discord.ui import Modal, InputText, View, Button

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


class PollVoteView:
    """Manages Discord native poll-based voting workflow."""

    def __init__(self,
                 author: str,
                 draft_name: str,
                 draft_url: str,
                 required_votes: int = 3,
                 duration_hours: float = 24.0):
        self.author = author
        self.draft_name = draft_name
        self.draft_url = draft_url
        self.required_votes = required_votes
        self.duration_hours = duration_hours
        self.result: Optional[str] = None  # "approve", "reject", "tie", or None
        self.approve_count = 0
        self.reject_count = 0
        self.end_time = int((datetime.now() + timedelta(hours=duration_hours)).timestamp())

    def create_poll(self) -> Poll:
        """Create the Discord poll object."""
        question = PollMedia(
            text=f"Vote: {self.draft_name} by {self.author}"
        )

        answers = [
            PollAnswer(text="Approve", emoji="✅"),
            PollAnswer(text="Reject", emoji="❌")
        ]

        # Duration in hours (Discord API expects hours as integer)
        duration = int(self.duration_hours)

        return Poll(
            question=question,
            answers=answers,
            duration=duration,
            allow_multiselect=False
        )

    def create_status_embed(self) -> discord.Embed:
        """Create embed with vote context."""
        embed = discord.Embed(
            title=f"📊 Vote: {self.draft_name}",
            description=(
                f"**Author:** {self.author}\n"
                f"**Draft:** [View Draft]({self.draft_url})\n\n"
                f"**Required votes:** {self.required_votes}\n"
                f"**Duration:** {self.duration_hours} hours\n"
                f"**Ends:** <t:{self.end_time}:R>\n\n"
                f"Vote using the poll below. "
                f"First option to reach {self.required_votes} votes wins."
            ),
            color=discord.Color.blue()
        )
        return embed

    async def monitor_and_wait(self,
                               message: discord.Message,
                               check_interval: int = 10) -> Optional[str]:
        """
        Monitor poll results until threshold reached or timeout.

        Returns:
            "approve" if approve threshold reached
            "reject" if reject threshold reached
            "tie" if both thresholds reached simultaneously
            None if timeout
        """
        start_time = time.time()
        duration_seconds = self.duration_hours * 3600
        check_count = 0

        logger.info(f"Starting poll monitor for {self.draft_name} - "
                   f"required: {self.required_votes}, duration: {self.duration_hours}h")

        while time.time() - start_time < duration_seconds:
            await asyncio.sleep(check_interval)
            check_count += 1

            try:
                # Fetch fresh message to get updated poll results
                message = await message.channel.fetch_message(message.id)
                poll = message.poll

                if not poll or not poll.results:
                    continue

                # Get vote counts (answer IDs start at 1)
                answer_counts = poll.results.answer_counts
                self.approve_count = answer_counts[0].count  # Approve
                self.reject_count = answer_counts[1].count   # Reject

                # Log periodically (every 6 minutes with 10s interval)
                if check_count % 36 == 0:
                    log_vote(f"Poll check for {self.draft_name}: "
                            f"Approve {self.approve_count}, Reject {self.reject_count}")

                # Check if threshold reached
                approve_threshold = self.approve_count >= self.required_votes
                reject_threshold = self.reject_count >= self.required_votes

                if approve_threshold and reject_threshold:
                    # Both reached threshold - determine winner
                    if self.approve_count > self.reject_count:
                        self.result = "approve"
                    elif self.reject_count > self.approve_count:
                        self.result = "reject"
                    else:
                        self.result = "tie"

                    log_vote(f"Poll threshold reached for {self.draft_name}: "
                            f"{self.result.upper()} ({self.approve_count} approve, "
                            f"{self.reject_count} reject)")
                    return self.result

                elif approve_threshold:
                    self.result = "approve"
                    log_vote(f"Poll threshold reached for {self.draft_name}: "
                            f"APPROVE ({self.approve_count} votes)")
                    return "approve"

                elif reject_threshold:
                    self.result = "reject"
                    log_vote(f"Poll threshold reached for {self.draft_name}: "
                            f"REJECT ({self.reject_count} votes)")
                    return "reject"

            except discord.NotFound:
                log_vote(f"Poll message deleted for {self.draft_name}")
                logger.error(f"Vote message was deleted for {self.draft_name}")
                return None

            except discord.HTTPException as e:
                logger.error(f"Failed to fetch poll results for {self.draft_name}: {e}")
                # Continue monitoring; may be temporary API issue
                continue

        # Timeout reached
        log_vote(f"Poll timed out for {self.draft_name}: "
                f"{self.approve_count} approve, {self.reject_count} reject "
                f"(needed {self.required_votes})")
        return None


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

            # Create poll vote view
            poll_view = PollVoteView(
                author=author,
                draft_name=draft_name,
                draft_url=draft.url,
                required_votes=required_votes,
                duration_hours=duration
            )

            # Create poll and embed
            poll = poll_view.create_poll()
            embed = poll_view.create_status_embed()

            # Send poll
            message = await ctx.followup.send(embed=embed, poll=poll)

            log_vote(f"Poll vote started for {draft_name} by {author} - "
                    f"required: {required_votes}, duration: {duration}h")

            # Monitor poll for threshold or timeout
            result = await poll_view.monitor_and_wait(message)

            # Handle timeout
            if result is None:
                timeout_embed = discord.Embed(
                    title="⏱️ Vote Timed Out",
                    description=(
                        f"Vote for **{draft_name}** by {author} has timed out.\n\n"
                        f"Final tally:\n"
                        f"✅ Approve: {poll_view.approve_count}\n"
                        f"❌ Reject: {poll_view.reject_count}\n\n"
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
                        f"Final tally: {poll_view.approve_count}-{poll_view.reject_count}\n\n"
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
                f"Final tally: {poll_view.approve_count} approve, {poll_view.reject_count} reject\n\n"
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
                        f"Final vote: {poll_view.approve_count} approve, "
                        f"{poll_view.reject_count} reject"
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
                        f"Final vote: {poll_view.approve_count} approve, "
                        f"{poll_view.reject_count} reject"
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