import disnake
import sqlite3
from disnake.ext import commands
from collections import namedtuple
__all__ = ['Setting', 'register_config']

async def noop(*_): pass
DatabaseHooks = namedtuple('DatabaseHooks', ('getter', 'contains', 'setter'))
# todo: dont store _value locally--interface w sqlite3 or smth so data persists
class Setting:
    def __init__(self, type_: disnake.OptionType, description:str=None, name:str=None):
        self.type_ = type_
        self.description = description
        self.name = name

        self._hooks: DatabaseHooks = None

    async def get(self, guild: disnake.Guild):
        if self._hooks is None: return None
        return await self._hooks.getter(guild)

    async def set(self, guild: disnake.Guild, value):
        if self._hooks is None: raise RuntimeError("Setter called before registration")
        await self._hooks.setter(guild, value)

    def __contains__(self, guild: disnake.Guild):
        if self._hooks is None: return None
        return self._hooks.contains(guild)

def register_config(bot: commands.Bot, cursor: sqlite3.Cursor):

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            cog   TEXT    NOT NULL,
            name  TEXT    NOT NULL,
            guild INTEGER NOT NULL,
            value TEXT    NOT NULL,
            PRIMARY KEY (cog, name, guild))""")

    perms = disnake.Permissions.none()
    perms.manage_guild = True

    # no-op function, used to bypass the function callback in command groups
    async def noop(*_): pass
    base_command: commands.InvokableSlashCommand = bot.slash_command(name="config", default_member_permissions=perms)(noop)

    def _config_callback(cog: commands.Cog, setting_name: str):
        async def _inner(inter: disnake.ApplicationCommandInteraction, value):
            if inter.guild is None: return
            await getattr(cog, setting_name).set(inter.guild, value)
            # todo: wrap these sorts of messages in embeds
            await inter.response.send_message("Option updated.", ephemeral=True)
        return _inner

    def _get_database_hooks(type_: disnake.OptionType, cog_name: str, setting_name: str):

        async def _getter(guild: disnake.Guild, default=None):
            cursor.execute("SELECT value FROM config WHERE cog=? AND name=? AND guild=?",
                           (cog_name, setting_name, guild.id))
            value = cursor.fetchone()
            if value is None: return default
            value = value[0]

            if type_ == disnake.OptionType.string:
                return value
            elif type_ == disnake.OptionType.integer:
                return int(value)
            elif type_ == disnake.OptionType.number:
                return float(value)
            elif type_ == disnake.OptionType.boolean:
                return value == "True"
            elif type_ == disnake.OptionType.user:
                return await guild.getch_member(int(value))
            elif type_ == disnake.OptionType.channel:
                return guild.get_channel(int(value))
            elif type_ == disnake.OptionType.role:
                return guild.get_role(int(value))
            elif type_ == disnake.OptionType.mentionable:
                ret = guild.get_role(int(value))
                if ret is None: ret = await guild.getch_member(int(value))
                return ret

        def _contains(guild: disnake.Guild, default=None):
            cursor.execute("SELECT value FROM config WHERE cog=? AND name=? AND guild=?",
                           (cog_name, setting_name, guild.id))
            value = cursor.fetchone()
            return value is not None

        async def _setter(guild: disnake.Guild, value):
            if type_ in (disnake.OptionType.integer, disnake.OptionType.number, disnake.OptionType.boolean):
                value = str(value)
            if type_ in (disnake.OptionType.user, disnake.OptionType.channel, disnake.OptionType.role, disnake.OptionType.mentionable):
                value = value.id
            cursor.execute("INSERT OR REPLACE INTO config(cog, name, guild, value) VALUES(?, ?, ?, ?)",
                           (cog_name, setting_name, guild.id, value))
            cursor.connection.commit()

        return DatabaseHooks(_getter, _contains, _setter)


    for cogname, cog in bot.cogs.items():

        # get all Setting class variables from the cog
        cogvars = cog.__class__.__dict__.items()
        cogvars = filter(lambda x: isinstance(x[1], Setting), cogvars)
        if not cogvars: continue

        group = base_command.sub_command_group(name=cogname.lower())(noop)

        # add commands to all settings
        for varname, setting in cogvars:
            hook_type = setting.type_
            setting_name = setting.name if setting.name else varname.lower()
            setting_description = setting.description if setting.description else f"Sets '{setting_name}' config setting for '{cogname}'"
            if isinstance(setting.type_, disnake.Option):
                option = setting.type_
                hook_type = hook_type.type
            else:
                option = disnake.Option(
                    name="value",
                    description="The new value",
                    type=setting.type_,
                    required=True)
            setting._hooks = _get_database_hooks(hook_type, cogname.lower(), setting_name)
            group.sub_command(name=setting_name, description=setting_description, options=[option])(_config_callback(cog, varname))
