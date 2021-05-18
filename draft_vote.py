import discord
from discord.ext import commands


class DraftVote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vote_id = 0

    @commands.command(name='vote')
    async def vote(self, ctx: commands.Context, status, name, title):
        await ctx.message.delete()
        if status == 'start':
            page = discord.Embed(title=f"Vote for Draft: {title} by {name}", description="",
                                 color=discord.Color.from_rgb(36, 255, 0))
            message = await ctx.send(embed=page)
            await message.add_reaction('🟢')
            await message.add_reaction('🔴')
            self.vote_id = message.id
        if status == 'end':
            nmsg = await ctx.channel.fetch_message(self.vote_id)
            reactions = nmsg.reactions

            final_count = discord.Embed(title=f"Results for Draft: {title} by {name}",
                                        color=discord.Color.from_rgb(36, 255, 0))
            if reactions[0].count > reactions[1].count:
                final_count.description = f'Approved\n{str(reactions[0])} **| {str(reactions[0].count)}**\n' \
                                          f'\n{str(reactions[1])}  **|  {str(reactions[1].count)}**'
            else:
                final_count.description = f'Rejected\n{str(reactions[0])} **| {str(reactions[0].count)}**\n' \
                                          f'\n{str(reactions[1])}  **|  {str(reactions[1].count)}**'
            await ctx.send(embed=final_count)


def setup(bot: commands.Bot):
    bot.add_cog(DraftVote(bot))
