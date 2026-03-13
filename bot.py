import os
import random
import json
import datetime
from collections import defaultdict
import psutil
import time
from datetime import timedelta
import asyncio
import sqlite3

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

# ---------------- SQLITE ECONOMY ---------------- #

DEV_ID = 1378768035187527795

conn = sqlite3.connect("economy.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS economy(
    user_id INTEGER PRIMARY KEY,
    wallet INTEGER,
    bank INTEGER,
    wins INTEGER,
    losses INTEGER
)
""")

conn.commit()

def create_account(user):

    cursor.execute(
        "SELECT * FROM economy WHERE user_id=?",
        (user.id,)
    )

    if cursor.fetchone() is None:

        cursor.execute(
            "INSERT INTO economy VALUES(?,?,?,?,?)",
            (user.id,1000,0,0,0)
        )

        conn.commit()

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

    embed.add_field(
        name="Economy",
        value="`.balance`\n`.deposit`\n`.withdraw`\n`.give`\n`.claim`\n`.roulette`",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------- ECONOMY COMMANDS ---------------- #

@bot.command()
async def balance(ctx, member: discord.Member=None):

    member = member or ctx.author
    create_account(member)

    cursor.execute(
        "SELECT wallet,bank FROM economy WHERE user_id=?",
        (member.id,)
    )

    wallet, bank = cursor.fetchone()

    embed = discord.Embed(
        title="Tony Stark Economy",
        color=0x2b2d31
    )

    embed.add_field(name="Wallet", value=f"🪙 {wallet:,}")
    embed.add_field(name="Bank", value=f"🏦 {bank:,}")

    await ctx.send(embed=embed)

@bot.command()
async def deposit(ctx, amount:int):

    create_account(ctx.author)

    cursor.execute(
        "SELECT wallet,bank FROM economy WHERE user_id=?",
        (ctx.author.id,)
    )

    wallet, bank = cursor.fetchone()

    if amount > wallet:
        return await ctx.send("Not enough money.")

    wallet -= amount
    bank += amount

    cursor.execute(
        "UPDATE economy SET wallet=?, bank=? WHERE user_id=?",
        (wallet,bank,ctx.author.id)
    )

    conn.commit()

    await ctx.send(f"Deposited **{amount:,}** coins.")

@bot.command()
async def withdraw(ctx, amount:int):

    create_account(ctx.author)

    cursor.execute(
        "SELECT wallet,bank FROM economy WHERE user_id=?",
        (ctx.author.id,)
    )

    wallet, bank = cursor.fetchone()

    if amount > bank:
        return await ctx.send("Not enough bank balance.")

    bank -= amount
    wallet += amount

    cursor.execute(
        "UPDATE economy SET wallet=?, bank=? WHERE user_id=?",
        (wallet,bank,ctx.author.id)
    )

    conn.commit()

    await ctx.send(f"Withdrew **{amount:,}** coins.")

@bot.command()
async def claim(ctx):

    create_account(ctx.author)

    reward = random.randint(500,2000)

    cursor.execute(
        "UPDATE economy SET wallet = wallet + ? WHERE user_id=?",
        (reward, ctx.author.id)
    )

    conn.commit()

    await ctx.send(f"You claimed **{reward:,} coins**.")

# ---------------- ROULETTE ---------------- #

bets = {}
roulette_running = False

@bot.command()
async def roulette(ctx, amount:int, bet:str):

    global roulette_running

    create_account(ctx.author)

    cursor.execute(
        "SELECT wallet FROM economy WHERE user_id=?",
        (ctx.author.id,)
    )

    wallet = cursor.fetchone()[0]

    if wallet < amount:
        return await ctx.send("Not enough money.")

    cursor.execute(
        "UPDATE economy SET wallet = wallet - ? WHERE user_id=?",
        (amount, ctx.author.id)
    )

    conn.commit()

    bets[ctx.author.id] = {
        "amount": amount,
        "bet": bet.lower()
    }

    await ctx.send(f"Bet **{amount}** on **{bet}**.")

    if not roulette_running:

        roulette_running = True

        await ctx.send("Roulette spinning in **30 seconds**...")

        await asyncio.sleep(30)

        await spin_roulette(ctx)

async def spin_roulette(ctx):

    global bets, roulette_running

    color = random.choice(["red","black","green"])
    number = random.randint(0,36)

    winners = []

    for uid,data in bets.items():

        amount = data["amount"]
        bet = data["bet"]

        win = False
        payout = 0

        if bet == color:
            payout = amount * 2
            win = True

        if bet.isdigit() and int(bet) == number:
            payout = amount * 35
            win = True

        if win:

            cursor.execute(
                "UPDATE economy SET wallet = wallet + ?, wins = wins + 1 WHERE user_id=?",
                (payout, uid)
            )

            winners.append(f"<@{uid}> won {payout}")

        else:

            cursor.execute(
                "UPDATE economy SET losses = losses + 1 WHERE user_id=?",
                (uid,)
            )

    conn.commit()

    embed = discord.Embed(
        title="Roulette Result",
        description=f"Color: **{color}**\nNumber: **{number}**"
    )

    if winners:
        embed.add_field(name="Winners", value="\n".join(winners))
    else:
        embed.add_field(name="Winners", value="No winners.")

    await ctx.send(embed=embed)

    bets = {}
    roulette_running = False

# ---------------- RUN ---------------- #

bot.run(TOKEN)