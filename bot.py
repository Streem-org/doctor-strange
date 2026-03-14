import os
import random
import json
import datetime
import asyncio
import time
import psutil
from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

start_time = time.time()

COUNTING_CHANNEL = 1477918309696667800

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"
DUOS_FILE = "duos.json"
BLACKLIST_FILE = "blacklist.json"

# ---------------- SAFE FILE FUNCTIONS ---------------- #

def safe_load(file):
    try:
        with open(file, "r") as f:
            data = f.read().strip()
            if not data:
                return {}
            return json.loads(data)
    except:
        return {}

def safe_save(file, data):
    temp = file + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(temp, file)

# ---------------- CREATE FILES ---------------- #

for file in [TIME_FILE, WEEKLY_FILE, DUOS_FILE, BLACKLIST_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# ---------------- DATA ---------------- #

afk_users = {}

weekly_messages = defaultdict(int)
weekly_data = safe_load(WEEKLY_FILE)

duos = safe_load(DUOS_FILE)
duo_requests = {}

times = safe_load(TIME_FILE)

blacklist = safe_load(BLACKLIST_FILE)
if isinstance(blacklist, dict):
    blacklist = []

count_number = 0
last_counter = None

eightball_responses = [
    "Yes",
    "No",
    "Ask again later",
    "It is certain",
    "Reply hazy, try later",
    "Not in the mood shut the fuck up",
    "I forgot the question"
]

# ---------------- BOT ---------------- #

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    help_command=None
)

# ---------------- READY ---------------- #

@bot.event
async def on_ready():

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="Training again")
    )

    if not weekly_reset.is_running():
        weekly_reset.start()

    print(f"Logged in as {bot.user}")

    bot.loop.create_task(terminal_listener())

# ---------------- TERMINAL COMMAND SYSTEM ---------------- #

async def terminal_listener():
    await bot.wait_until_ready()

    while not bot.is_closed():

        cmd = await asyncio.to_thread(input)

        if cmd.startswith("say "):

            try:
                parts = cmd.split(" ",2)
                channel_id = int(parts[1])
                msg = parts[2]

                channel = bot.get_channel(channel_id)

                if channel:
                    await channel.send(msg)

            except:
                print("Invalid format: say CHANNEL_ID message")

# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():

    global weekly_data

    weekly_data = {}
    weekly_messages.clear()

    safe_save(WEEKLY_FILE, weekly_data)

# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):

    global count_number, last_counter

    if message.author.bot:
        return

    if message.author.id in blacklist:
        return

    weekly_messages[message.author.id] += 1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]

    safe_save(WEEKLY_FILE, weekly_data)

    await bot.process_commands(message)

# ---------------- BLACKLIST ---------------- #

@bot.command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, member: discord.Member):

    if member.id in blacklist:
        await ctx.send("User already blacklisted.")
        return

    blacklist.append(member.id)
    safe_save(BLACKLIST_FILE, blacklist)

    await ctx.send(f"🚫 {member.mention} blacklisted.")


@bot.command()
@commands.has_permissions(administrator=True)
async def unblacklist(ctx, member: discord.Member):

    if member.id not in blacklist:
        await ctx.send("User not blacklisted.")
        return

    blacklist.remove(member.id)
    safe_save(BLACKLIST_FILE, blacklist)

    await ctx.send(f"✅ {member.mention} removed from blacklist.")

# ---------------- TIME SYSTEM ---------------- #

@bot.command()
async def time(ctx, sub=None, *, value=None):

    if sub == "set":

        import pytz

        try:
            pytz.timezone(value)
        except:
            await ctx.send("Invalid timezone.")
            return

        times[str(ctx.author.id)] = value
        safe_save(TIME_FILE, times)

        embed = discord.Embed(
            description=f"Timezone set to **{value}**",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)
        return

    member = ctx.message.mentions[0] if ctx.message.mentions else ctx.author

    if str(member.id) not in times:

        embed = discord.Embed(
            description=f"{member.mention} has not set timezone.\nUse `.time set Asia/Kolkata`",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)
        return

    import pytz

    tz = pytz.timezone(times[str(member.id)])
    now = datetime.datetime.now(tz)

    embed = discord.Embed(
        title=f"{member.display_name}'s Time",
        color=discord.Color.blurple()
    )

    embed.add_field(name="Time", value=now.strftime("%I:%M %p"))
    embed.add_field(name="Date", value=now.strftime("%d %B %Y"))
    embed.add_field(name="Timezone", value=times[str(member.id)], inline=False)

    await ctx.send(embed=embed)

# ---------------- REBOOT ---------------- #

@bot.command()
@commands.is_owner()
async def reboot(ctx):

    await ctx.send("♻️ Rebooting...")
    os.execv(__file__, ["python"] + os.sys.argv)

# ---------------- RUN BOT ---------------- #

bot.run(TOKEN)