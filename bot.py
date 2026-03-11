import os
import time
import random
import json
import datetime
from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv
import pytz

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

CREATOR_ID = 1378768035187527795
COUNTING_CHANNEL = 1477918309696667800
ROLE_DROP_CHANNEL = 1469526304738119940
STAFF_EVIDENCE_CHANNEL = 1481206250623598725

TIME_FILE = "times.json"

# ---------------- DATA ---------------- #

start_time = time.time()

afk_users = {}
weekly_messages = defaultdict(int)

count_number = 0
last_counter = None

blacklisted_users = set()

duos = {}

eightball_responses = [
"Yes","No","Streem loves his hg ask later",
"Ronlx wants penalty reply later",
"Absolutely not","Ask again later",
"Probably","I don't think so",
"Without a doubt","Very likely"
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

# ---------------- FILE ---------------- #

if not os.path.exists(TIME_FILE):
    with open(TIME_FILE,"w") as f:
        json.dump({},f)

def load_times():
    with open(TIME_FILE,"r") as f:
        return json.load(f)

def save_times(data):
    with open(TIME_FILE,"w") as f:
        json.dump(data,f,indent=4)

# ---------------- EMBED ---------------- #

def magic_embed(ctx,title,question=None,answer=None):

    embed = discord.Embed(
        title=title,
        color=discord.Color.blurple()
    )

    if question:
        embed.add_field(name="Info",value=question,inline=False)

    if answer:
        embed.add_field(name="Result",value=answer,inline=False)

    embed.set_footer(
        text=ctx.guild.name,
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    return embed

# ---------------- EVENTS ---------------- #

@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")

@bot.event
async def on_message(message):

    global count_number,last_counter

    if message.author.bot:
        return

    if message.author.id in blacklisted_users:
        return

    weekly_messages[message.author.id]+=1

    if message.author.id in afk_users:

        del afk_users[message.author.id]

        embed = discord.Embed(
            description=f"{message.author.mention} is no longer AFK",
            color=discord.Color.blurple()
        )

        await message.channel.send(embed=embed)

    for user in message.mentions:

        if user.id in afk_users:

            embed = discord.Embed(
                title="AFK User",
                description=afk_users[user.id],
                color=discord.Color.blurple()
            )

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

    await bot.process_commands(message)

# ---------------- HELP ---------------- #

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Bot Commands",
        description="Prefix: `.`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value="`.avatar`\n`.uptime`\n`.time`",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="`.8ball`\n`.ship`",
        inline=False
    )

    embed.add_field(
        name="Duo",
        value="`.match @user`\n`.us`",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="`.blacklist`\n`.unblacklist`\n`.ev p`",
        inline=False
    )

    embed.add_field(
        name="Owner",
        value="`.shutdown`",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------- UTILITY ---------------- #

@bot.command()
async def uptime(ctx):

    seconds=int(time.time()-start_time)
    uptime=str(timedelta(seconds=seconds))

    embed = magic_embed(ctx,"Bot Uptime","Running Time",uptime)

    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx,member:discord.Member=None):

    member = member or ctx.author

    embed = magic_embed(ctx,"Avatar",member.mention)

    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ---------------- FUN ---------------- #

@bot.command(name="8ball")
async def eightball(ctx,*,question):

    reply=random.choice(eightball_responses)

    embed = magic_embed(ctx,"Magic 8ball",question,reply)

    await ctx.send(embed=embed)

# ---------------- TIME ---------------- #

@bot.command()
async def time(ctx):

    data = load_times()
    tz = data.get(str(ctx.author.id))

    if not tz:
        await ctx.send("Set timezone using `.timeset <zone>`")
        return

    now=datetime.datetime.now(
        pytz.timezone(tz)
    ).strftime("%I:%M %p")

    embed=magic_embed(ctx,"Your Time",now,tz)

    await ctx.send(embed=embed)

# ---------------- SHUTDOWN ---------------- #

@bot.command()
async def shutdown(ctx):

    if ctx.author.id!=CREATOR_ID:
        return

    await ctx.send("Shutting down... 👋🏼")

    await bot.close()

# ---------------- EVIDENCE ---------------- #

@bot.group()
async def ev(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.message.delete()

@ev.command()
async def p(ctx):

    if not ctx.message.reference:
        await ctx.message.delete()
        return

    ref = ctx.message.reference
    msg = await ctx.channel.fetch_message(ref.message_id)

    staff_channel = bot.get_channel(STAFF_EVIDENCE_CHANNEL)

    embed = discord.Embed(
        description=f"**{msg.author.display_name} said:**\n\n{msg.content}",
        color=discord.Color.dark_theme()
    )

    files=[]
    for attachment in msg.attachments:
        files.append(await attachment.to_file())

    await staff_channel.send(embed=embed,files=files)

    await ctx.message.delete()

# ---------------- MATCH SYSTEM ---------------- #

class MatchView(discord.ui.View):

    def __init__(self, requester, target):
        super().__init__(timeout=60)
        self.requester=requester
        self.target=target

    @discord.ui.button(label="Accept",style=discord.ButtonStyle.green)
    async def accept(self,interaction:discord.Interaction,button:discord.ui.Button):

        if interaction.user!=self.target:
            await interaction.response.send_message(
                "Not your request.",ephemeral=True)
            return

        duos[self.requester.id]=self.target.id
        duos[self.target.id]=self.requester.id

        embed=discord.Embed(
            title="Duo Created",
            description=f"{self.requester.mention} 🤝 {self.target.mention}",
            color=discord.Color.green()
        )

        await interaction.response.edit_message(embed=embed,view=None)

    @discord.ui.button(label="Decline",style=discord.ButtonStyle.red)
    async def decline(self,interaction:discord.Interaction,button:discord.ui.Button):

        if interaction.user!=self.target:
            await interaction.response.send_message(
                "Not your request.",ephemeral=True)
            return

        await interaction.response.edit_message(
            content="Duo request declined.",
            view=None
        )

@bot.command()
async def match(ctx,member:discord.Member):

    if member.bot:
        await ctx.send("You can't duo with bots.")
        return

    if member==ctx.author:
        await ctx.send("You can't duo yourself.")
        return

    if ctx.author.id in duos:
        await ctx.send("You already have a duo.")
        return

    if member.id in duos:
        await ctx.send("That user already has a duo.")
        return

    view=MatchView(ctx.author,member)

    await ctx.send(
        f"{member.mention}, **{ctx.author.display_name}** wants to duo with you!",
        view=view
    )

@bot.command()
async def us(ctx):

    if ctx.author.id not in duos:
        await ctx.send("You don't have a duo yet.")
        return

    partner_id=duos[ctx.author.id]
    partner=ctx.guild.get_member(partner_id)

    embed=discord.Embed(
        title="Your Duo",
        description=f"{ctx.author.mention} 🤝 {partner.mention}",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)

# ---------------- RUN ---------------- #

bot.run(TOKEN)