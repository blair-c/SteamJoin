from os import getenv
from sys import version
from typing import Literal

import discord
from discord.ext import commands
import redis
import requests

print(f'Python {version}\n'
      f'discord.py {discord.__version__} | '
      f'hiredis-py {redis.__version__} | '
      f'requests {requests.__version__}')


class MyBot(commands.Bot):

    def __init__(self, *, intents: discord.Intents):
        super().__init__(
            activity=discord.CustomActivity(name='/invite | steamjoin.com'),
            command_prefix=commands.when_mentioned,
            intents=intents
        )
    
    async def setup_hook(self):
        cogs = [
            'invite',  # Steam invite command
        ]
        for cog in cogs:
            await self.load_extension(f'cogs.{cog}')
            print(f'Loaded {cog} cog...')
        print(f'Logged in as {bot.user}\nUser ID: {bot.user.id}')


intents = discord.Intents.default()
intents.members = True
bot = MyBot(intents=intents)
bot.remove_command('help')

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, scope: Literal['global', 'guild']):
    """Sync global or guild commands"""
    async with ctx.channel.typing():
        if scope == 'global':
            synced = await ctx.bot.tree.sync()
            txt = 'globally'
        elif scope == 'guild':
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
            txt = 'to the current guild'
    await ctx.send(f'Synced {len(synced)} commands {txt}')

@bot.command()
async def about(ctx: commands.Context):
        """About SteamJoin"""
        desc = f'```ml\n{len(bot.guilds):,} servers / {len(bot.users):,} users```'
        embed = discord.Embed(description=desc, color=1908518)
        embed.set_author(
            name='About SteamJoin',
            icon_url=bot.user.display_avatar.url)
        embed.add_field(
            name='Developed by blair',
            value='https://blair-c.github.io',
            inline=False)
        embed.add_field(
            name='Source Code',
            value='https://github.com/blair-c/SteamJoin',
            inline=False)
        await ctx.send(embed=embed)

if __name__ == '__main__':
    bot.run(getenv('TOKEN'))  # https://discord.com/developers/applications
