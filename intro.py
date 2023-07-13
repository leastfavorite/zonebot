import disnake
from disnake.ext import commands

elevated_perms = disnake.Permissions.none()
elevated_perms.manage_guild = True

class PronounModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Pronouns",
                placeholder="e.g. she/her, they/he",
                custom_id="pronouns",
                style=disnake.TextInputStyle.short,
                max_length=25,
            )
        ]
        super().__init__(title="Set your pronouns:", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        pronouns = inter.text_values["pronouns"]
        role_name = f"PRONOUNS: {pronouns}"
        for role in inter.author.roles:
            if role.name.startswith("PRONOUNS: "):
                await inter.author.remove_roles(role)
                if len(role.members) == 0:
                    await role.delete()

        for role in inter.guild.roles:
            if role.name == role_name:
                await inter.author.add_roles(role)
                await inter.response.send_message(embed=disnake.Embed(
                    title="Success", description=f"Pronouns updated: `{pronouns}`",
                    color=disnake.Color.green()), ephemeral=True)

        role = await inter.guild.create_role(name=role_name)
        await inter.author.add_roles(role)
        await inter.response.send_message(embed=disnake.Embed(
            title="Success", description=f"Pronouns updated: `{pronouns}`",
            color=disnake.Color.green()), ephemeral=True)


class RoleModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Role Name",
                placeholder="get creative. idk",
                custom_id="name",
                style=disnake.TextInputStyle.single_line,
                min_length=3,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="Role Color",
                placeholder="e.g. #123456, #FFD0B0",
                custom_id="color",
                style=disnake.TextInputStyle.short,
                min_length=7,
                max_length=7,
                required=False
            )
        ]
        super().__init__(title="Set your custom role:", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        name = inter.text_values["name"]
        color_name = inter.text_values["color"]

        kwargs = {}
        if color_name:
            try:
                color = disnake.Color(int(color_name[1:], 16))
                if color == disnake.Color(0): raise ValueError()
            except ValueError:
                await inter.response.send_message(embed=disnake.Embed(
                    title="Error", description=f"Invalid color: `{color}`",
                    color=disnake.Color.red()), ephemeral=True)
                return
            kwargs["color"] = color
        kwargs["name"] = name

        for role in inter.author.roles:
            if role.color != disnake.Color(0):
                await role.edit(**kwargs)
                await inter.response.send_message(embed=disnake.Embed(
                    title="Success", description=f"Role updated: `{name}`",
                    color=disnake.Color.green()), ephemeral=True)
                return

        role = await inter.guild.create_role(
            name=name, color=color, permissions=disnake.Permissions.none())
        await inter.author.add_roles(role)
        await inter.response.send_message(embed=disnake.Embed(
            title="Success", description=f"Role updated: `{name}`",
            color=color), ephemeral=True)

class IntroView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(
        label="Set Pronouns", style=disnake.ButtonStyle.primary, custom_id="intro:pronouns", emoji="\U0001f3f3\uFE0F\u200D\u26A7\uFE0F")
    async def pronouns(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=PronounModal())

    @disnake.ui.button(
        label="Set Role", style=disnake.ButtonStyle.primary, custom_id="intro:role", emoji=u"\U0001F60E")
    async def role(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=RoleModal())

_PERMS = disnake.Permissions.none()
_PERMS.manage_guild = True

class Intro(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(IntroView())

    @commands.slash_command(description="Sends the intro message", default_member_permissions=_PERMS)
    async def send_intro_message(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title=u"\N{SUNFLOWER} Welcome! \N{SUNFLOWER}",
            description="Please use these buttons to set your pronouns and custom role.",
            color=disnake.Color(0xFF8000))
        await inter.channel.send(embed=embed, view=IntroView())
        await inter.response.send_message("Sent.", ephemeral=True)

