import disnake
from disnake.ext import commands

# todo: dont store _value locally--interface w sqlite3 or smth so data persists
class Setting:
    def __init__(self, type_: disnake.OptionType, description:str=None, name:str=None):
        self.type_ = type_
        self.description = description
        self.name = name
        self._value = {}

    def __getitem__(self, guild):
        return self._value.get(guild)

    def __contains__(self, guild: disnake.Guild):
        return guild in self._value

    def __setitem__(self, guild: disnake.Guild, value):
        # todo: config function to write to database
        self._value[guild] = value

def register_config(bot: commands.Bot):

    # no-op function, used to bypass the function callback in command groups
    async def noop(*_): pass
    base_command: commands.InvokableSlashCommand = bot.slash_command(name="config")(noop)

    def _config_callback(cog: commands.Cog, setting_name: str):
        async def _inner(inter: disnake.ApplicationCommandInteraction, value):
            if inter.guild is None: return
            getattr(cog, setting_name)[inter.guild] = value
            # todo: wrap these sorts of messages in embeds
            await inter.response.send_message("Option updated.", ephemeral=True)
        return _inner

    for cogname, cog in bot.cogs.items():

        # get all Setting class variables from the cog
        cogvars = cog.__class__.__dict__.items()
        cogvars = filter(lambda x: isinstance(x[1], Setting), cogvars)
        if not cogvars: continue

        group = base_command.sub_command_group(name=cogname.lower())(noop)

        # add commands to all settings
        for varname, setting in cogvars:
            # todo: grab values from database
            setting_name = setting.name if setting.name else varname.lower()
            setting_description = setting.description if setting.description else f"Sets '{setting_name}' config setting for '{cogname}'"
            if isinstance(setting.type_, disnake.Option):
                option = setting.type_
            else:
                option = disnake.Option(
                    name="value",
                    description="The new value",
                    type=setting.type_,
                    required=True)
            group.sub_command(name=setting_name, description=setting_description, options=[option])(_config_callback(cog, varname))
