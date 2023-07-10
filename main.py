import os
import disnake
import argparse
import logging

from vc import Vc
from config import register_config
from disnake.ext import commands


parser = argparse.ArgumentParser(prog="ZoneBot", description="A Discord Bot")
parser.add_argument('--production', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

logging.basicConfig(level=(logging.DEBUG if args.verbose else logging.INFO))

bot_kwargs = {
    "intents": disnake.Intents.default(),
    "command_sync_flags": commands.CommandSyncFlags.default(),
}
bot_kwargs["intents"].members = True
bot_kwargs["command_sync_flags"].sync_commands_debug = not args.production

if not args.production:
    if "GUILD_ID" not in os.environ:
        raise RuntimeError("Specify test guild ID in GUIlD_ID environment variable, or run with --production")
    bot_kwargs["test_guilds"] = [int(os.environ["GUILD_ID"])]

bot = commands.InteractionBot(**bot_kwargs)
bot.add_cog(Vc(bot))
register_config(bot)
bot.run(os.environ["DISCORD_KEY"])
