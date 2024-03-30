import json, requests
from os import getenv
from urllib.parse import quote

import discord
from discord import app_commands, ui
from discord.ext import commands
import redis

r = redis.Redis.from_url(getenv('REDIS_URL'))
STEAMKEY = getenv('STEAMKEY')
COLOR = 1908518


async def invite(interaction: discord.Interaction, steamid: str, ping: discord.Member, update_db=False):
    """Final logic once Steam ID is set."""
    resp = requests.get(
        url='https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/'
            f'?key={STEAMKEY}&steamids=[{steamid}]')
    resp = resp.json()['response']['players']
    try:
        info = resp[0]
    except IndexError:
        embed = discord.Embed(title='Error: Invalid Steam ID', color=COLOR)
        view = ui.View()
        view.add_item(SetSteamButton(name='Try Another', user=interaction.user, ping=ping))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return
    if update_db:
        r.set(interaction.user.id, info['steamid'])
    # Invite
    if info.get('communityvisibilitystate') == 1:
        embed = discord.Embed(title='Error: Private Profile', color=COLOR)
        embed.set_author(name=info['personaname'], url=info['profileurl'], icon_url=info['avatar'])
        view = ui.View()
        view.add_item(RetryButton(user=interaction.user, steamid=info['steamid'], ping=ping))
        view.add_item(SetSteamButton(name='Not you?', user=interaction.user, ping=ping))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    elif not info.get('gameid'):
        desc = 'Make sure "Game details" are set to "Public" in Privacy Settings'
        embed = discord.Embed(title='Error: Not Publicly In-Game', description=desc, color=COLOR)
        embed.set_author(name=info['personaname'], url=info['profileurl'], icon_url=info['avatar'])
        embed.set_image(url='https://steamjoin.com/img/privacy-settings.png')
        view = ui.View()
        view.add_item(RetryButton(user=interaction.user, steamid=info['steamid'], ping=ping))
        view.add_item(SetSteamButton(name='Not you?', user=interaction.user, ping=ping))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    elif not info.get('lobbysteamid'):
        desc = ''
        if info['gameid'] == '383980':  # RoA
            desc = 'Create a new, empty friendlies match lobby, then retry'
        embed = discord.Embed(title='Error: No Joinable Game Lobby Found', description=desc, color=COLOR)
        embed.set_author(name=info['personaname'], url=info['profileurl'], icon_url=info['avatar'])
        if info['gameid'] == '383980':  # RoA
            embed.set_image(url='https://steamjoin.com/img/lobby-roa.png')
        view = ui.View()
        view.add_item(RetryButton(user=interaction.user, steamid=info['steamid'], ping=ping))
        view.add_item(SetSteamButton(name='Not you?', user=interaction.user, ping=ping))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:  # Success
        lobbylink = f"https://steamjoin.com/{info['profileurl'].rstrip('/').split('/')[-1]}"
        embed = discord.Embed(
            title=f"Playing {info['gameextrainfo']}",
            description=f'Join Game: {lobbylink}',
            color=COLOR)
        embed.set_author(name=info['personaname'], url=info['profileurl'], icon_url=info['avatar'])
        await interaction.response.send_message(content=ping.mention, embed=embed)


class RetryButton(ui.Button):
    """Button to retry invite."""
    def __init__(self, user: discord.User, steamid: str, ping: discord.Member):
        self.user = user
        self.steamid = steamid
        self.ping = ping
        super().__init__(label='Retry', style=discord.ButtonStyle.blurple)

    async def callback(self, interaction):
        if self.user == interaction.user:
            await invite(interaction=interaction, steamid=self.steamid, ping=self.ping)
        else:
            return


class SetSteamButton(ui.Button):
    """Button to bring up Steam Modal."""
    def __init__(self, name: str, user: discord.User, ping: discord.Member):
        self.user = user
        self.ping = ping
        super().__init__(label=name, style=discord.ButtonStyle.gray)

    async def callback(self, interaction):
        if self.user == interaction.user:
            await interaction.response.send_modal(SteamModal(ping=self.ping))
        else:
            return


class SteamModal(ui.Modal):
    """Resolve Steam ID from user input, then proceed with invite."""
    def __init__(self, ping: discord.Member):
        self.ping = ping
        super().__init__(title="What's your Steam?")

    user_input = ui.TextInput(label='Steam ID or URL', placeholder='https://steamcommunity.com/...')

    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.user_input.value
        user_input = user_input.replace('https://', '')
        user_input = user_input.replace('steamcommunity.com/', '')
        user_input = user_input.replace('id/', '')
        user_input = user_input.replace('profiles/', '')
        user_input = user_input.replace('/', '')
        user_input = quote(user_input)
        if not user_input.isdigit():  # Vanity URL to Steam ID
            resp = requests.get(
                url='https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
                    f'?key={STEAMKEY}&vanityurl={user_input}')
            resp = resp.json()['response']
            if resp['success'] == 1:
                user_input = resp['steamid']
        await invite(interaction=interaction, steamid=user_input, ping=self.ping, update_db=True)


class Invite(commands.Cog):
    """Steam invite command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='Invite to Lobby',
            callback=self.invite_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def invite_menu(self, interaction: discord.Interaction, ping: discord.Member):
        """Invite a user with your Steam "Join Game" lobby link"""
        if steamid := r.get(interaction.user.id):
            await invite(interaction=interaction, steamid=steamid, ping=ping)
        else:
            await interaction.response.send_modal(SteamModal(ping=ping))

    @app_commands.command(name='invite')
    async def invite_cmd(self, interaction: discord.Interaction, ping: discord.Member):
        """Invite user with Steam "Join Game" lobby link"""
        if steamid := r.get(interaction.user.id):
            await invite(interaction=interaction, steamid=steamid, ping=ping)
        else:
            await interaction.response.send_modal(SteamModal(ping=ping))


async def setup(bot: commands.Bot):
    await bot.add_cog(Invite(bot))
