import os
import random
import json
import datetime
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

COUNTING_CHANNEL = 1477918309696667800

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"

bot_start_time = datetime.datetime.utcnow()

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

    temp_file = file + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(data, f, indent=4)

    os.replace(temp_file, file)

# ---------------- DATA ---------------- #

afk_users = {}

weekly_messages = defaultdict(int)
weekly_data = safe_load(WEEKLY_FILE)

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
        activity=discord.Game(name="Jarvis protocols")
    )

    if not weekly_reset.is_running():
        weekly_reset.start()

    print(f"Logged in as {bot.user}")

# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():

    global weekly_data

    weekly_data = {}
    safe_save(WEEKLY_FILE, weekly_data)

# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):

    global count_number, last_counter

    if message.author.bot:
        return

    # COMMANDS FIRST
    await bot.process_commands(message)

    # weekly tracking
    weekly_messages[message.author.id] += 1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]
    safe_save(WEEKLY_FILE, weekly_data)

    # AFK REMOVE
    if message.author.id in afk_users:

        del afk_users[message.author.id]

        embed = discord.Embed(
            description="Your AFK has been removed.",
            color=discord.Color.red()
        )

        await message.channel.send(
            content=message.author.mention,
            embed=embed
        )

    # AFK MENTION
    for user in message.mentions:

        if user.id in afk_users:

            reason = afk_users[user.id]

            embed = discord.Embed(
                description=f"{user.mention} is currently AFK",
                color=discord.Color.orange()
            )

            embed.add_field(name="Reason", value=reason)

            await message.channel.send(embed=embed)

    # COUNTING SYSTEM
    if message.channel.id == COUNTING_CHANNEL:

        try:
            number = int(message.content)
        except:
            await message.delete()
            return

        if number != count_number + 1:
            await message.delete()
            return

        if last_counter == message.author.id:
            await message.delete()
            return

        count_number = number
        last_counter = message.author.id

# ---------------- HELP ---------------- #

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Jarvis Command Panel",
        description="Prefix: `.`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value="`.avatar`\n`.uptime`\n`.afk`",
        inline=False
    )

    embed.add_field(
        name="Weekly",
        value="`.wk`\n`.wk p @user`",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="`.8ball`\n`.ship`",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)

# ---------------- AFK ---------------- #

@bot.command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = reason

    embed = discord.Embed(
        description=f"{ctx.author.mention} is now AFK.",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Reason",
        value=reason,
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------- WEEKLY ---------------- #

@bot.command()
async def wk(ctx, sub=None, member: discord.Member=None):

    if sub is None:

        if not weekly_data:
            await ctx.send("No weekly data yet.")
            return

        sorted_data = sorted(
            weekly_data.items(),
            key=lambda x: x[1],
            reverse=True
        )

        desc = ""

        for i, (user_id, points) in enumerate(sorted_data[:10], start=1):

            user = ctx.guild.get_member(int(user_id))

            if user:
                desc += f"**{i}. {user.name}** — {points} messages\n"

        embed = discord.Embed(
            title="Weekly Leaderboard",
            description=desc,
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

    elif sub == "p":

        member = member or ctx.author
        points = weekly_data.get(str(member.id), 0)

        embed = discord.Embed(
            title="Weekly Stats",
            description=f"{member.mention} sent **{points} messages** this week.",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

# ---------------- UPTIME ---------------- #

@bot.command()
async def uptime(ctx):

    now = datetime.datetime.utcnow()
    uptime = now - bot_start_time

    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    embed = discord.Embed(
        title="Bot Uptime",
        description=f"{days}d {hours}h {minutes}m {seconds}s",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)

# ---------------- AVATAR ---------------- #

@bot.command()
async def avatar(ctx, member: discord.Member=None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=discord.Color.blurple()
    )

    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ---------------- 8BALL ---------------- #

@bot.command(name="8ball")
async def eightball(ctx, *, question):

    question_lower = question.lower()
    reply = random.choice(eightball_responses)

    if "are you gay" in question_lower or "are u gay" in question_lower:
        reply = "I may or may not be gay, but you seem to be."

    embed = discord.Embed(title="Magic 8ball")

    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=reply, inline=False)

    await ctx.send(embed=embed)

# ---------------- SHIP ---------------- #

@bot.command()
async def ship(ctx, member: discord.Member=None):

    user1 = ctx.author
    user2 = member or ctx.author

    if user1 == user2:
        await ctx.send("You need someone else.")
        return

    percent = random.randint(0, 100)

    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)

    embed = discord.Embed(
        title=f"{user1.name} ❤️ {user2.name}",
        description=f"`{bar}` {percent}%",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)

# ---------------- RUN ---------------- #

bot.run(TOKEN)