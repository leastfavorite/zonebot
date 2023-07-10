import disnake
from disnake.ext import commands, tasks
from typing import Optional
from config import Setting

class Vc(commands.Cog):
    vc_role = Setting(disnake.OptionType.role, "Role to give members of VCs", name="role")

    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def _update_member(self, member: disnake.Member):
        if not (role := self.vc_role[member.guild]): return
        state = member.voice
        has_role = role in member.roles
        if state is None or state.deaf or state.self_deaf or state.afk \
                or not isinstance(state.channel, disnake.VoiceChannel):
            if has_role: await member.remove_roles(role)
        else:
            if not has_role: await member.add_roles(role)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        await self._update_member(member)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.resync_vc_role()

    @tasks.loop(minutes=30)
    async def resync_vc_role(self):
        for guild in self.bot.guilds:
            role: disnake.Role = self.vc_role[guild]
            if role is None: continue
            candidates = set()
            candidates.update(role.members)
            for channel in guild.voice_channels:
                if channel is guild.afk_channel: continue
                candidates.update(channel.members)
            for candidate in candidates:
                await self._update_member(candidate)
