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
                max_length=25
            )
        ]
        super().__init__(title="Set your pronouns:", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.send_message(inter.text_values["pronouns"], ephemeral=True)

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
                return

        role = await inter.guild.create_role(name=role_name)
        await role.edit(position=1)
        await inter.author.add_roles(role)


class RoleModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Role Name",
                placeholder="get creative. idk",
                custom_id="name",
                style=disnake.TextInputStyle.single_line,
                max_length=100
            ),
            disnake.ui.TextInput(
                label="Role Color",
                placeholder="e.g. #123456, #FFD0B0",
                custom_id="color",
                style=disnake.TextInputStyle.short,
                min_length=7,
                max_length=7
            )
        ]
        super().__init__(title="Set your custom role:", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            color = disnake.Color(int(inter.text_values["color"][1:], 16))
        except ValueError:
            color = inter.text_values["color"]
            await inter.response.send_message(embed=disnake.Embed(
                title="Error", description=f"Invalid color: `{color}`",
                color=disnake.Color.red()), ephemeral=True)
            return
        await inter.response.send_message(inter.text_values["name"], ephemeral=True)

class IntroView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(
        label="Set Pronouns", style=disnake.ButtonStyle.primary, custom_id="intro:pronouns")
    async def pronouns(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=PronounModal())

    @disnake.ui.button(
        label="Set Role", style=disnake.ButtonStyle.primary, custom_id="intro:role")
    async def role(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=RoleModal())

class Intro(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(IntroView())

    @commands.slash_command(description="Sends the intro message")
    async def send_intro_message(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title=u"\N{SUNFLOWER} Welcome! \N{SUNFLOWER}",
            description="Please use these buttons to set your pronouns and custom role.",
            color=disnake.Color(0xFF8000))
        await inter.channel.send(embed=embed, view=IntroView())
        await inter.response.send_message("Sent.", ephemeral=True)

