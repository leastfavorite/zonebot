import disnake
from disnake.ext import commands
import sqlite3
from dataclasses import dataclass

@dataclass(frozen=True)
class ButtonEntry:
    name: str
    emoji: str
    role: disnake.Role

class RoleButton(disnake.ui.Button):
    def __init__(self, entry: ButtonEntry):
        self.role: disnake.Role = entry.role
        super().__init__(
            style=disnake.ButtonStyle.primary, label=entry.name,
            custom_id=f"roles:{entry.role.name}", emoji=entry.emoji)

    async def callback(self, inter: disnake.MessageInteraction):
        if self.role in inter.author.roles:
            await inter.author.remove_roles(self.role)
            await inter.response.send_message(embed=disnake.Embed(
                title="Role added", description=f"Role {self.role.mention} removed.",
                color=disnake.Color.red()), ephemeral=True)
            return
        await inter.author.add_roles(self.role)
        await inter.response.send_message(embed=disnake.Embed(
            title="Role removed", description=f"Role {self.role.mention} added.",
            color=disnake.Color.green()), ephemeral=True)
        return

class RoleView(disnake.ui.View):
    def __init__(self, roles: list[ButtonEntry]):
        super().__init__(timeout=None)
        for role in roles:
            self.add_item(RoleButton(role))


_PERMS = disnake.Permissions.none()
_PERMS.manage_guild = True
class Roles(commands.Cog):

    def __init__(self, bot: commands.InteractionBot, cursor: sqlite3.Cursor):
        self.bot = bot
        self.cur = cursor
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                guild INTEGER NOT NULL,
                role INTEGER NOT NULL,
                name TEXT NOT NULL,
                emoji TEXT NOT NULL,
                PRIMARY KEY (guild, role))""")
        self.views = {}

    @commands.Cog.listener()
    async def on_ready(self):
        self.cur.execute("""SELECT DISTINCT guild FROM roles""")
        while (fetch := self.cur.fetchmany(20)):
            for index in fetch:
                guild = self.bot.get_guild(index[0])
                if guild is not None:
                    self._update_view(guild)

    def _update_view(self, guild: disnake.Guild):
        self.cur.execute(
            """SELECT name, emoji, role FROM roles WHERE guild=? ORDER BY rowid ASC""",
            (guild.id,))
        values = self.cur.fetchmany(5)
        roles = [y for y in (ButtonEntry(x[0],x[1], guild.get_role(x[2])) \
                 for x in values) if y.role is not None]

        view = RoleView(roles)
        if guild.id in self.views:
            # dont think theres a better way to do this
            self.bot._connection._view_store.remove_view(self.views[guild.id])
        self.views[guild.id] = view
        self.bot.add_view(view)

    @commands.slash_command(description="Sends the role message", default_member_premissions=_PERMS)
    async def send_role_message(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title=u"\N{SUNFLOWER} Roles \N{Sunflower}",
            description="Click to toggle each role.",
            color=disnake.Color(0xFF8000))
        await inter.channel.send(embed=embed, view=self.views[inter.guild.id])
        await inter.response.send_message("Sent.", ephemeral=True)

    @commands.slash_command(description="Adds a role.",
                            default_member_permissions=_PERMS)
    async def add_role(self, inter: disnake.ApplicationCommandInteraction,
                       name: str, emoji: str, role: disnake.Role):
        self.cur.execute(
            """INSERT OR REPLACE INTO roles(guild, role, name, emoji) VALUES(?, ?, ?, ?)""",
            (role.guild.id, role.id, name, emoji))
        self.cur.connection.commit()
        self._update_view(role.guild)
        await inter.response.send_message("Role added.", ephemeral=True)

    @commands.slash_command(description="Removes a role.",
                            default_member_permissions=_PERMS)
    async def remove_role(self, inter: disnake.ApplicationCommandInteraction,
                          role: disnake.Role):
        self.cur.execute(
            """DELETE FROM roles WHERE guild=? AND role=?""",
            (role.guild.id, role.id))
        self.cur.connection.commit()
        self._update_view(role.guild)
        await inter.response.send_message("Role removed.", ephemeral=True)
