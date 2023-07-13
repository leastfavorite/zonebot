import disnake
from disnake.ext import commands
import sqlite3
import aiohttp
import json
# probably not as portable enough to pass a code review
# but whatever
# :p

class UsernameStorage:
    def __init__(self, cur: sqlite3.Cursor, whitelist: str):
        self.cur = cur
        self.whitelist = whitelist

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                snowflake INTEGER NOT NULL,
                username  TEXT NOT NULL,
                uuid      TEXT NOT NULL,
                PRIMARY KEY (snowflake))""")

    def as_json(self):
        self.cur.execute("""SELECT username, uuid FROM whitelist""")
        out = []
        format_ = lambda s: f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
        while (fetch := self.cur.fetchmany(20)):
            out.extend({"name": x[0], "uuid": format_(x[1])} for x in fetch)
        return json.dumps(out)

    async def add_username(self, user: disnake.User, username: str):

        async with aiohttp.ClientSession("https://api.mojang.com/") as session:
            async with session.get(f"/users/profiles/minecraft/{username}") as r:
                if r.status != 200:
                    return None
                else:
                    response = await r.json()
                    uuid = response["id"]
                    username = response["name"]
                    self.cur.execute("INSERT OR REPLACE INTO whitelist(snowflake, username, uuid) VALUES(?, ?, ?)",
                                     (user.id, username, uuid))
                    self.cur.connection.commit()
                    self.update_whitelist()
                    return username

    async def get_username(self, user: disnake.User):
        self.cur.execute("SELECT username, uuid FROM whitelist WHERE snowflake=?", (user.id,))
        fetch = self.cur.fetchone()
        if fetch is None: return None
        name = fetch[0]
        uuid = fetch[1]
        
        async with aiohttp.ClientSession("https://sessionserver.mojang.com/") as session:
            async with session.get(f"/session/minecraft/profile/{uuid}") as r:
                if r.status != 200:
                    return None
                else:
                    response = await r.json()
                    if name != response["name"]:
                        self.cur.execute(
                            "REPLACE INTO whitelist(snowflake, username, uuid) VALUES(?, ?, ?)",
                            (user.id, response["name"], uuid))
                        self.cur.connection.commit()
                    return response["name"]

    # opens the whitelist and copies from table
    def update_whitelist(self):
        with open(self.whitelist, "w") as f:
            f.write(self.as_json())

class WhitelistModal(disnake.ui.Modal):
    def __init__(self, storage: UsernameStorage, old_username=None):
        self.storage = storage
        components = [
            disnake.ui.TextInput(
                label="Username",
                placeholder=old_username if old_username else "",
                custom_id="username",
                style=disnake.TextInputStyle.short
            )
        ]
        super().__init__(title="Get whitelisted", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        username = inter.text_values["username"]
        user = inter.author

        success = await self.storage.add_username(user, username)

        if success:
            await inter.response.send_message(embed=disnake.Embed(
                title="Success", description=f"`{username}` added to whitelist.",
                color=disnake.Color.green()), ephemeral=True)
        else:
            await inter.response.send_message(embed=disnake.Embed(
                title="Error", description=f"Could not find `{username}`.",
                color=disnake.Color.red()), ephemeral=True)

class WhitelistView(disnake.ui.View):
    def __init__(self, storage: UsernameStorage):
        self.storage = storage
        super().__init__(timeout=None)

    @disnake.ui.button(
        label="Join Whitelist", style=disnake.ButtonStyle.primary,
        custom_id="whitelist:add", emoji="\U0001F4DD")
    async def whitelist(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        username = await self.storage.get_username(inter.author)
        await inter.response.send_modal(
            modal=WhitelistModal(self.storage, old_username=username))

_PERMS = disnake.Permissions.none()
_PERMS.manage_guild = True

class Whitelist(commands.Cog):
    def __init__(self, bot: commands.InteractionBot, cursor: sqlite3.Cursor, whitelist: str):
        self.storage = UsernameStorage(cursor, whitelist)
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(WhitelistView(self.storage))
        self.storage.update_whitelist()

    @commands.slash_command(description="Sends the whitelist message",
                                default_member_permissions=_PERMS)
    async def send_whitelist_message(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title=u"\N{SUNFLOWER} Whitelist \N{SUNFLOWER}",
            description="Hit the button below to add yourself to the server whitelist.",
            color=disnake.Color(0xFF8000))
        await inter.channel.send(embed=embed, view=WhitelistView(self.storage))
        await inter.response.send_message("Sent.", ephemeral=True)

