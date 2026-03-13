import os
import random
import json
import datetime
from collections import defaultdict
import psutil
import time
from datetime import timedelta
import asyncio

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
    temp = file + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(temp, file)

# ---------------- DATA ---------------- #

afk_users = {}

weekly_messages = defaultdict(int)
weekly_data = safe_load(WEEKLY_FILE)

duos = safe_load(DUOS_FILE)
duo_requests = {}

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

    await bot.process_commands(message)

    weekly_messages[message.author.id] += 1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]
    safe_save(WEEKLY_FILE, weekly_data)

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

    for user in message.mentions:

        if user.id in afk_users:

            reason = afk_users[user.id]

            embed = discord.Embed(
                description=f"{user.mention} is currently AFK",
                color=discord.Color.orange()
            )

            embed.add_field(name="Reason", value=reason)

            await message.channel.send(embed=embed)

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
        value="`.8ball`\n`.ship`\n`.match`\n`.duo`\n`.unmatch`",
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

    embed.add_field(name="Reason", value=reason)

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

        for i,(user_id,points) in enumerate(sorted_data[:10],start=1):

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
        points = weekly_data.get(str(member.id),0)

        embed = discord.Embed(
            title="Weekly Stats",
            description=f"{member.mention} sent **{points} messages** this week.",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

# ---------------- UPTIME ---------------- #
@bot.command()
async def uptime(ctx):

    # Bot uptime
    bot_seconds = int(time.time() - start_time)
    bot_uptime = str(timedelta(seconds=bot_seconds))

    bot_started = datetime.datetime.fromtimestamp(
        start_time
    ).strftime("%d %B %Y %I:%M %p")

    # System uptime
    system_seconds = int(time.time() - psutil.boot_time())
    system_uptime = str(timedelta(seconds=system_seconds))

    system_started = datetime.datetime.fromtimestamp(
        psutil.boot_time()
    ).strftime("%d %B %Y %I:%M %p")

    embed = discord.Embed(
        title="Uptime Information",
        color=discord.Color.dark_theme()
    )

    embed.add_field(
        name="I was last rebooted",
        value="`0 days ago`",
        inline=False
    )

    embed.add_field(
        name="Bot Uptime",
        value=f"{bot_uptime}\n• {bot_started}",
        inline=False
    )

    embed.add_field(
        name="System Uptime",
        value=f"{system_uptime}\n• {system_started}",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
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

    reply = random.choice(eightball_responses)

    if "are u gay" in question.lower() or "are you gay" in question.lower():
        reply = "I may or may not be gay, but you seem to be."

    embed = discord.Embed(title="Magic 8ball")

    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=reply, inline=False)

    await ctx.send(embed=embed)

# ---------------- SHIP ---------------- #
@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member):

    percent = random.randint(0, 100)

    # ship name
    name1 = user1.display_name[:len(user1.display_name)//2]
    name2 = user2.display_name[len(user2.display_name)//2:]
    shipname = name1 + name2

    # compatibility bar
    filled = int(percent / 5)
    bar = "█" * filled + " " * (20 - filled)

    embed = discord.Embed(
        title=shipname,
        description=f"```{bar} {percent}%```",
        color=discord.Color.pink()
    )

    embed.add_field(
        name=" ",
        value=f"{user1.mention} ❤️ {user2.mention}",
        inline=False
    )

    embed.set_thumbnail(url=user1.display_avatar.url)
    embed.set_image(url=user2.display_avatar.url)

    embed.set_footer(
        text=f"Shipped by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)
# ---------------- DUO SYSTEM ---------------- #

@bot.command()
async def match(ctx, member: discord.Member):

    if str(ctx.author.id) in duos:
        await ctx.send("You already have a duo.")
        return

    duo_requests[member.id] = ctx.author.id

    embed = discord.Embed(
        title="Duo Request",
        description=f"{ctx.author.mention} wants to duo with {member.mention}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    embed.add_field(
        name="Accept",
        value=f"{member.mention} type `.accept`",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def accept(ctx):

    if ctx.author.id not in duo_requests:
        await ctx.send("No duo request.")
        return

    requester = duo_requests[ctx.author.id]

    duos[str(ctx.author.id)] = str(requester)
    duos[str(requester)] = str(ctx.author.id)

    safe_save(DUOS_FILE, duos)

    del duo_requests[ctx.author.id]

    embed = discord.Embed(
        title="Duo Created ❤️",
        description=f"<@{requester}> ❤️ {ctx.author.mention}",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)

@bot.command()
async def duo(ctx):

    if str(ctx.author.id) not in duos:
        await ctx.send("You don't have a duo.")
        return

    partner = ctx.guild.get_member(int(duos[str(ctx.author.id)]))

    embed = discord.Embed(
        title="Your Duo",
        description=f"{ctx.author.mention} ❤️ {partner.mention}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=partner.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
async def unmatch(ctx):

    if str(ctx.author.id) not in duos:
        await ctx.send("You don't have a duo.")
        return

    partner = duos[str(ctx.author.id)]

    duos.pop(str(ctx.author.id),None)
    duos.pop(str(partner),None)

    safe_save(DUOS_FILE,duos)

    await ctx.send("💔 Duo removed.")

# ---------------- ROLE DROP SYSTEM ---------------- #

import json
import os
import discord
from discord.ext import commands

ROLEDROP_FILE = "roledrop_winners.json"
EXECUTOR_ROLE_ID = 1481903901656481812
MESSI_ROLE_ID = 1476264072809943091
CRISTIANO_ROLE_ID = 1476262979010957414
OWNER_FAVOURITE_ID = 1476260723297489019
ALLOWED_DROP_ROLES = [MESSI_ROLE_ID, CRISTIANO_ROLE_ID,OWNER_FAVOURITE_ID]

# create storage file
if not os.path.exists(ROLEDROP_FILE):
    with open(ROLEDROP_FILE, "w") as f:
        json.dump({}, f)

def load_roledrop():
    with open(ROLEDROP_FILE, "r") as f:
        return json.load(f)

def save_roledrop(data):
    with open(ROLEDROP_FILE, "w") as f:
        json.dump(data, f, indent=4)


@bot.hybrid_command()
async def roledrop(ctx, role: discord.Role):

    # check executor permission
    executor_role = ctx.guild.get_role(EXECUTOR_ROLE_ID)

    if executor_role not in ctx.author.roles:
     await ctx.send("❌ You cannot execute this command.")
    return

    # only allow specific roles to be dropped
    if role.id not in ALLOWED_DROP_ROLES:
        await ctx.send("❌ You can only drop the Messi or Cristiano roles.")
        return

    winners = load_roledrop()

    content= "@everyone"
    embed= discord.Embed(
        title="🎉 Role Drop",
        description=f"Reply to this message to win {role.mention}!",
        color=discord.Color.gold()
    )

    drop_message = await ctx.send(embed=embed)

    def check(m):
        return (
            m.channel == ctx.channel
            and m.reference
            and m.reference.message_id == drop_message.id
            and not m.author.bot
        )

    try:
        msg = await bot.wait_for("message", timeout=30, check=check)

        role_id = str(role.id)
        user_id = str(msg.author.id)

        winners.setdefault(role_id, [])

        # prevent duplicate wins
        if user_id in winners[role_id]:
            await ctx.send(f"{msg.author.mention} already won **{role.name}** before.")
            return

        await msg.author.add_roles(role)

        winners[role_id].append(user_id)
        save_roledrop(winners)

        win = discord.Embed(
            description=f"🏆 {msg.author.mention} won **{role.name}**!",
            color=discord.Color.green()
        )

        await ctx.send(embed=win)

    except:
        await ctx.send("⏱️ No one claimed the role in time.")

# ---------------- ECONOMY STORAGE ---------------- #

DEV_ID = 1378768035187527795

import os

def load_data():
    if not os.path.exists("economy.json"):
        with open("economy.json", "w") as f:
            json.dump({}, f)

    with open("economy.json", "r") as f:
        return json.load(f)


def save_data(data):
    with open("economy.json", "w") as f:
        json.dump(data, f, indent=4)


economy = load_data()


def create_account(user):

    uid = str(user.id)

    if uid not in economy:

        economy[uid] = {
            "wallet": 1000,
            "bank": 0,
            "wins": 0,
            "losses": 0
        }

        save_data(economy)

@bot.event
async def on_member_join(member):
    create_account(member)

# ---------------- BALANCE ---------------- #

@bot.command()
async def balance(ctx, member: discord.Member=None):

    member = member or ctx.author
    create_account(member)

    data = economy[str(member.id)]

    embed = discord.Embed(
        title="Tony Stark Economy",
        color=0x2b2d31
    )

    embed.set_author(name="Tony Stark", icon_url=bot.user.avatar.url)

    embed.add_field(name="Wallet", value=f"🪙 {data['wallet']:,}", inline=True)
    embed.add_field(name="Bank", value=f"🏦 {data['bank']:,}", inline=True)

    await ctx.send(embed=embed)


# ---------------- WALLET ---------------- #

@bot.command()
async def wallet(ctx):
    await balance(ctx, ctx.author)


# ---------------- DEPOSIT ---------------- #

@bot.command()
async def deposit(ctx, amount:int):

    create_account(ctx.author)
    user = economy[str(ctx.author.id)]

    if amount > user["wallet"]:
        return await ctx.send("Not enough money.")

    user["wallet"] -= amount
    user["bank"] += amount

    save_data(economy)

    embed = discord.Embed(
        title="Deposit Successful",
        description=f"Deposited **{amount:,}** coins.",
        color=0x2ecc71
    )

    await ctx.send(embed=embed)


# ---------------- WITHDRAW ---------------- #

@bot.command()
async def withdraw(ctx, amount:int):

    create_account(ctx.author)
    user = economy[str(ctx.author.id)]

    if amount > user["bank"]:
        return await ctx.send("Not enough money in bank.")

    user["bank"] -= amount
    user["wallet"] += amount

    save_data(economy)

    embed = discord.Embed(
        title="Withdraw Successful",
        description=f"Withdrew **{amount:,}** coins.",
        color=0xf1c40f
    )

    await ctx.send(embed=embed)


# ---------------- GIVE ---------------- #

@bot.command()
async def give(ctx, member:discord.Member, amount:int):

    create_account(ctx.author)
    create_account(member)

    sender = economy[str(ctx.author.id)]
    receiver = economy[str(member.id)]

    if sender["wallet"] < amount:
        return await ctx.send("You don't have that much.")

    sender["wallet"] -= amount
    receiver["wallet"] += amount

    save_data(economy)

    embed = discord.Embed(
        title="Money Sent",
        description=f"{ctx.author.mention} gave **{amount:,}** coins to {member.mention}",
        color=0x3498db
    )

    await ctx.send(embed=embed)


# ---------------- CLAIM ---------------- #

@bot.command()
async def claim(ctx):

    create_account(ctx.author)

    reward = random.randint(500, 2000)

    economy[str(ctx.author.id)]["wallet"] += reward

    save_data(economy)

    embed = discord.Embed(
        title="Daily Reward",
        description=f"You received **{reward:,} coins**.",
        color=0x9b59b6
    )

    await ctx.send(embed=embed)


# ---------------- LEADERBOARD ---------------- #

@bot.command()
async def leaderboard(ctx):

    ranking = sorted(
        economy.items(),
        key=lambda x: x[1]["wallet"] + x[1]["bank"],
        reverse=True
    )

    text = ""

    for i,(uid,data) in enumerate(ranking[:10], start=1):

        user = bot.get_user(int(uid))
        total = data["wallet"] + data["bank"]

        text += f"**{i}.** {user} — {total:,}\n"

    embed = discord.Embed(
        title="Tony Stark Economy Leaderboard",
        description=text,
        color=0xe67e22
    )

    await ctx.send(embed=embed)


# ---------------- GAMBLE STATS ---------------- #

@bot.command()
async def gamblestats(ctx):

    create_account(ctx.author)
    data = economy[str(ctx.author.id)]

    embed = discord.Embed(
        title="Gambling Statistics",
        color=0x7289da
    )

    embed.add_field(name="Wins", value=data["wins"])
    embed.add_field(name="Losses", value=data["losses"])

    await ctx.send(embed=embed)


# ---------------- ROULETTE SYSTEM ---------------- #

bets = {}
roulette_running = False


@bot.command()
async def roulette(ctx, amount:int, bet:str):

    global roulette_running

    create_account(ctx.author)
    user = economy[str(ctx.author.id)]

    if user["wallet"] < amount:
        return await ctx.send("Not enough money.")

    bet = bet.lower()

    valid_colors = ["red","black","green"]

    if bet not in valid_colors and not bet.isdigit():
        return await ctx.send("Invalid bet. Use red, black, green or number 0-36.")

    user["wallet"] -= amount
    save_data(economy)

    bets[ctx.author.id] = {
        "amount": amount,
        "bet": bet
    }

    embed = discord.Embed(
        title="Bet Placed",
        description=f"You placed **{amount:,}** on **{bet}**.",
        color=0x2b2d31
    )

    embed.add_field(name="Bet amount", value=f"🪙 {amount:,}", inline=True)
    embed.add_field(name="Bet type", value=bet.capitalize(), inline=True)

    await ctx.send(embed=embed)

    if not roulette_running:

        roulette_running = True

        start = discord.Embed(
            title="Place your bets!",
            description="The roulette wheel will spin in **30 seconds**.",
            color=0x2b2d31
        )

        await ctx.send(embed=start)

        await asyncio.sleep(30)

        await spin_roulette(ctx)



async def spin_roulette(ctx):

    global bets, roulette_running

    color = random.choice(["red","black","green"])
    number = random.randint(0,36)

    winners = []

    for uid,data in bets.items():

        bet = data["bet"]
        amount = data["amount"]

        win = False
        payout = 0

        if bet == color:
            win = True
            payout = amount * 2

        if bet.isdigit() and int(bet) == number:
            win = True
            payout = amount * 35

        if bet == "green" and color == "green":
            payout = amount * 14
            win = True

        if win:

            economy[str(uid)]["wallet"] += payout
            economy[str(uid)]["wins"] += 1

            winners.append(f"<@{uid}> — {payout:,}")

        else:
            economy[str(uid)]["losses"] += 1


    save_data(economy)

    embed = discord.Embed(
        title="Roulette Result",
        description=f"• The wheel lands on **{color.upper()}**\n• Winning number **{number}**",
        color=0xff0000 if color=="red" else 0x000000
    )

    if winners:
        embed.add_field(name="Winners", value="\n".join(winners), inline=False)
    else:
        embed.add_field(name="Winners", value="No one won this round.", inline=False)

    await ctx.send(embed=embed)

    bets = {}
    roulette_running = False


# ---------------- DEV COMMAND ---------------- #

@bot.command()
async def addmoney(ctx, member:discord.Member, amount:int):

    if ctx.author.id != DEV_ID:
        return

    create_account(member)

    economy[str(member.id)]["wallet"] += amount

    save_data(economy)

    await ctx.send(f"Gave {amount:,} coins to {member}.")


# ---------------- RUN ---------------- #

bot.run(TOKEN)