import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout


class DraftVote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tally = {
            "🟢": 0,
            "🔴": 0
        }
        self.record = {}

    async def vote(self, message, tallyMessage, name, title):
        if isinstance(name, str) and isinstance(title, str):
            while True:
                reaction, user = await asyncio.shield(self.bot.wait_for("reaction_add"))
                if str(user) != 'DraftReview#3678' and reaction.emoji in ['🟢', '🔴']:
                    await message.remove_reaction(reaction.emoji, user)

                    if user.name in self.record.keys() and self.record[user.name] != reaction.emoji:
                        string = "You have successfully changed your vote to " + reaction.emoji + " for " + \
                                 f"Draft: {title} by {name}"
                        await user.send(string)
                    elif user.name not in self.record.keys():
                        string = "You have successfully voted " + reaction.emoji + " for " + f"Draft: {title} by {name}"
                        await user.send(string)

                    if user.name in self.record.keys():
                        self.tally[self.record[user.name]] -= 1
                    self.tally[reaction.emoji] += 1

                    self.record[user.name] = reaction.emoji
                    tallyString = "```"
                    for names in self.record.keys():
                        if self.record[names] == '🟢':
                            tallyString += names + " voted yes." + "\n"
                        if self.record[names] == '🔴':
                            tallyString += names + " voted no." + "\n"
                    tallyString += "```"

                    tally = discord.Embed(title="Tally for " + f"Draft: {name} by {user}", description=tallyString,
                                          color=discord.Color.from_rgb(36, 255, 0))
                    tallyString = "``` Number of votes: " + str(len(self.record.keys())) + "```"
                    tally = discord.Embed(title="Votes for " + f"Draft: {title} by {name}", description=tallyString,
                                          color=discord.Color.from_rgb(36, 255, 0))
                    await tallyMessage.edit(embed=tally)
        else:
            while True:
                reaction, user = await asyncio.shield(self.bot.wait_for("reaction_add"))
                if str(user) != 'DraftReview#3678' and reaction.emoji in ['🟢', '🔴']:
                    await message.remove_reaction(reaction.emoji, user)

                    if user.name in self.record.keys() and self.record[user.name] != reaction.emoji:
                        string = "You have successfully changed your vote to " + reaction.emoji + " for " + \
                                 f"Draft: {title} by {name}"
                        await user.send(string)
                    elif user.name not in self.record.keys():
                        string = "You have successfully voted " + reaction.emoji + " for " + f"Draft: {title} by {name}"
                        await user.send(string)

                    if user.name in self.record.keys():
                        self.tally[self.record[user.name]] -= 1
                    self.tally[reaction.emoji] += 1

                    self.record[user.name] = reaction.emoji
                    tallyString = "```"
                    for names in self.record.keys():
                        if self.record[names] == '🟢':
                            tallyString += names + " voted yes." + "\n"
                        if self.record[names] == '🔴':
                            tallyString += names + " voted no." + "\n"
                    tallyString += "```"

                    tally = discord.Embed(title="Tally for " + f"Draft: {title} by {name}", description=tallyString,
                                          color=discord.Color.from_rgb(36, 255, 0))
                    await tallyMessage.edit(embed=tally)

                    tallyString = "``` Number of votes: " + str(len(self.record.keys())) + "```"
                    tally = discord.Embed(title="Votes for " + f"Draft: {title} by {name}", description=tallyString,
                                          color=discord.Color.from_rgb(36, 255, 0))
                    await message.edit(embed=tally)

    @commands.command(name='startvote')
    async def startvote(self, ctx: commands.Context, name, title, timeoutSeconds=86400):
        # try:
        await ctx.message.delete()
        page = discord.Embed(title=f"Vote for Draft: {title} by {name}", description="",
                             color=discord.Color.from_rgb(36, 255, 0))
        message = await ctx.send(embed=page)
        await message.add_reaction('🟢')
        await message.add_reaction('🔴')
        self.bot.remove_command('startvote')

        tallyString = "``` No one has voted ```"
        tally = discord.Embed(title=f"Tally for Draft: {title} by {name}", description=tallyString,
                              color=discord.Color.from_rgb(36, 255, 0))
        tallyMessage = await self.bot.get_channel(842662513400348684).send(embed=tally)

        try:
            async with timeout(timeoutSeconds):
                await self.vote(message, tallyMessage, name, title)
        except asyncio.TimeoutError:
            tallyString = "```Yes:" + "\t" + str(self.tally['🟢']) + "\nNo: \t" + str(self.tally["🔴"]) + "```"
            tally = discord.Embed(title=f"VOTE HAS ENDED for Draft: {title} by {name}", description=tallyString,
                                  color=discord.Color.from_rgb(36, 255, 0))
            await message.delete()
            await ctx.send(embed=tally)

        except TypeError:
            errorpage = discord.Embed(title="Error in voting", description=r"TypeError ¯\_(ツ)_/¯",
                                      color=discord.Color.from_rgb(36, 255, 0))
            await ctx.send(embed=errorpage)


def setup(bot: commands.Bot):
    bot.add_cog(DraftVote(bot))
