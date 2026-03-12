import os
import time
import random
import json
import datetime
from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from discord.ui import View
import pytz
import psutil

from PIL import Image, ImageDraw, ImageFont
import aiohttp
from io import BytesIO

bot_start_time = datetime.datetime.utcnow()

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

CREATOR_ID = 1378768035187527795
COUNTING_CHANNEL = 1477918309696667800
STAFF_EVIDENCE_CHANNEL = 1481206250623598725
ROLEDROP_USERS = (1378768035187527795,1214001826127421440)

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"

# ---------------- DATA ---------------- #

start_time = time.time()

afk_users = {}
afk_pings = {}

weekly_messages = defaultdict(int)

count_number = 0
last_counter = None

duos = {}

eightball_responses = [
"Yes","No","Ask again later",
"It is certain","Reply hazy, try later",
"Not in the mood shut the fuck up","I forgot the question"
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

# ---------------- AFK VIEW ---------------- #

class AFKReturnView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="Welcome Back", style=discord.ButtonStyle.green)
    async def welcome_back(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This button is not for you.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Your AFK has already been removed.",
            ephemeral=True
        )

# ---------------- FILES ---------------- #

if not os.path.exists(TIME_FILE):
    with open(TIME_FILE,"w") as f:
        json.dump({},f)

if not os.path.exists(WEEKLY_FILE):
    with open(WEEKLY_FILE,"w") as f:
        json.dump({},f)

def load_times():
    with open(TIME_FILE,"r") as f:
        return json.load(f)

def save_times(data):
    with open(TIME_FILE,"w") as f:
        json.dump(data,f,indent=4)

def load_weekly():
    with open(WEEKLY_FILE,"r") as f:
        return json.load(f)

def save_weekly(data):
    with open(WEEKLY_FILE,"w") as f:
        json.dump(data,f,indent=4)

weekly_data = load_weekly()

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
    save_weekly(weekly_data)

    print("Weekly leaderboard reset.")

# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):

    global count_number,last_counter

    if message.author.bot:
        return

    # weekly tracking
    weekly_messages[message.author.id]+=1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]
    save_weekly(weekly_data)

    # AFK remove
    if message.author.id in afk_users:

        del afk_users[message.author.id]

        embed=discord.Embed(
            description="Welcome back! Your AFK has been removed.",
            color=discord.Color.green()
        )

        view = AFKReturnView(message.author.id)

        await message.channel.send(
            content=message.author.mention,
            embed=embed,
            view=view
        )

    # AFK mention detect
    for user in message.mentions:

        if user.id in afk_users:

            reason = afk_users[user.id]

            afk_pings.setdefault(user.id,[])
            afk_pings[user.id].append(
                f"{message.author} in {message.channel.mention}"
            )

            embed=discord.Embed(
                description=f"{user.mention} is currently AFK",
                color=discord.Color.orange()
            )

            embed.add_field(name="Reason",value=reason)

            await message.channel.send(embed=embed)

    # counting system
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

    await bot.process_commands(message)

# ---------------- HELP ---------------- #

@bot.command()
async def help(ctx):

    embed=discord.Embed(
        title="Jarvis Command Panel",
        description="Prefix: `.`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value="`.avatar`\n`.uptime`\n`.afk`\n`.roledrop`",
        inline=False
    )

    embed.add_field(
        name="Time",
        value="`.time`\n`.timeset`\n`.timeremove`",
        inline=False
    )

    embed.add_field(
        name="Weekly",
        value="`.wk`\n`.wk p @user`",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="`.8ball`\n`.ship`\n`.choose`",
        inline=False
    )

    embed.add_field(
        name="Match",
        value="`.match @user`\n`.us`\n`.unmatch`",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="`.ev p` (reply to message)",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)

# ---------------- AFK COMMAND ---------------- #

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

# ---------------- WEEKLY COMMAND ---------------- #

@bot.command()
async def wk(ctx, sub=None, member: discord.Member=None):

    if sub is None:

        if not weekly_data:
            await ctx.send("No weekly data yet.")
            return

        sorted_data = sorted(
            weekly_data.items(),
            key=lambda x:x[1],
            reverse=True
        )

        desc=""

        for i,(user_id,points) in enumerate(sorted_data[:10],start=1):

            user=ctx.guild.get_member(int(user_id))

            if user:
                desc+=f"**{i}. {user.name}** — {points} messages\n"

        embed=discord.Embed(
            title="Weekly Leaderboard",
            description=desc,
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

    elif sub=="p":

        member = member or ctx.author
        points = weekly_data.get(str(member.id),0)

        embed=discord.Embed(
            title="Weekly Stats",
            description=f"{member.mention} sent **{points} messages** this week.",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

# ---------------- UTILITY ---------------- #

@bot.command()
async def uptime(ctx):

    now = datetime.datetime.utcnow()

    bot_uptime = now - bot_start_time
    bot_days = bot_uptime.days
    bot_hours, remainder = divmod(bot_uptime.seconds,3600)
    bot_minutes, bot_seconds = divmod(remainder,60)

    embed=discord.Embed(
        title="Bot Uptime",
        description=f"{bot_days}d {bot_hours}h {bot_minutes}m {bot_seconds}s",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx,member:discord.Member=None):

    member = member or ctx.author

    embed=discord.Embed(
        title=f"{member.name}'s Avatar",
        color=discord.Color.blurple()
    )

    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ---------------- FUN ---------------- #

@bot.command(name="8ball")
async def eightball(ctx,*,question):

    question_lower = question.lower()
    reply = random.choice(eightball_responses)

    if "are you gay" in question_lower or "are u gay" in question_lower:
        reply="I may or may not be gay, but you seem to be."

    embed=discord.Embed(title="Magic 8ball")

    embed.add_field(name="Question",value=question,inline=False)
    embed.add_field(name="Answer",value=reply,inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def ship(ctx,member:discord.Member=None):

    user1 = ctx.author
    user2 = member or ctx.author

    if user1==user2:
        await ctx.send("You need someone else.")
        return

    percent=random.randint(0,100)

    filled=int(percent/10)
    bar="█"*filled+"░"*(10-filled)

    embed=discord.Embed(
        title=f"{user1.name} ❤️ {user2.name}",
        description=f"`{bar}` {percent}%",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)

# ---------------- RUN ---------------- #

bot.run(TOKEN)