# TODO: Split the bot into: Commands & Function.
# Also make specific send-functions in order to allow functions to be only the function itself - not the one sending the message. Also this might help reudce code by alot.

import discord
import asyncio
import aiohttp
from discord.ext import commands
from discord.ext.commands import bot
from datetime import datetime, timedelta
import time

intents = discord.Intents.default()
intents.members = True
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix='$', intents=intents)


servers = {}


class VariablesForChecks:
    def __init__(self):
        self.fissure_check_started = False
        self.eidolon_check_started = False
        self.invasions_check_started = False


# TODO: Write a function to whisper members with a specific role and only if they want to!
# TODO: Write a function for people to sign up to specific whispering.
async def whisper_specific_members(ctx, specific_role, message="", embed=None):
    tmp = [member for member in ctx.guild.members if discord.utils.get(ctx.guild.roles, name=specific_role) in member.roles]
    for member in tmp:
        if member != bot.user:
            if embed is None:
                await member.send(message)
            elif message is "":
                await member.send(embed=embed)


async def create_fissure_embed(ctx, tier, node, mission):
    channel = bot.get_channel(812453448393031690)
    fembed = discord.Embed(
        title='Neue Risse',
        colour=discord.Colour.dark_purple()
    )

    fembed.add_field(name='Tier       ', value=tier, inline=True)
    fembed.add_field(name='Node       ', value=node, inline=True)
    fembed.add_field(name='Mission Type', value=mission, inline=True)
    await channel.send(embed=fembed)
    await whisper_specific_members(ctx, "Fissures", message="", embed=fembed)


async def get_all_data(url=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.warframestat.us/pc/{url}") as r:
            if r.status == 200:
                return await r.json()
        await session.close()


# TODO: Get rid of the global variable - see "inavsions_check" for reference.
async def eidolon_check(ctx):
    global eidolon_check_started
    channel = bot.get_channel(812422704719593513)
    if not eidolon_check_started:
        await channel.send("Beendigung des Eidolon Checks.")
    else:
        wd = await get_all_data("cetusCycle")
        isDay = wd['isDay']
        h, m, s = calculate_remaining_world_duration(wd)
        timeRemaining = ((h * 60) + m) * 60 + s

        await channel.send("Starting eidolon check.")
        while eidolon_check_started:
            if isDay:
                isDay = False
                print(f"Warten für {timeRemaining}, weil Tag ist.")
                await asyncio.sleep(timeRemaining)
                timeRemaining = 3000
            elif not isDay:
                isDay = True
                await channel.send(f"Es ist Nacht! Zeit für die Eidolon Jagd.")
                await whisper_specific_members(ctx, "Eidolon", "Es ist Nacht! Zeit für die Eidolon Jagd!")
                print(f"Warten für {timeRemaining}, weil Nacht ist.")
                await asyncio.sleep(timeRemaining)
                timeRemaining = 6000


# TODO: Get rid of the global variable - see "inavsions_check" for reference.
async def fissure_check(ctx):
    global fissure_check_started
    channel = bot.get_channel(812453448393031690)
    if not fissure_check_started:
        await channel.send("Beendigung des Fissure Checks!")
    else:
        await channel.send("Starting Fissure Check now. Checking every 5min")
        old = await get_all_data("fissures")
        old_ids = []
        for iterator in old:
            old_ids.append(iterator['id'])

        while fissure_check_started:
            print(f"Checking for new fissures")
            new = await get_all_data("fissures")
            new_ids = []
            tier, node, mission = "", "", ""
            for iterator in new:
                new_ids.append(iterator['id'])

            for fissure in new:
                if fissure['id'] not in old_ids:
                    tier += fissure['tier'] + "\n"
                    node += fissure['node'] + "\n"
                    mission += fissure['missionType'] + "\n"

            if tier != "":
                await create_fissure_embed(ctx, tier, node, mission)
                print("Neue Fissures gefunden.")
            old_ids = new_ids
            await asyncio.sleep(60)


async def invasions_check(ctx):
    old = []
    # look for the channel "Fissures" otherwise use the channel, where the command has been set up
    correct_channel = ctx.channel
    for channel in ctx.guild.channels:
        if channel.name == "invasions":
            correct_channel = channel
    if servers[ctx.guild.id].invasions_check_started:
        print(f"Invasion Check started for {ctx.guild.id}")
        while servers[ctx.guild.id].invasions_check_started:
            node, new_node = "", ""
            attackerReward, new_attackerReward = "", ""
            attacker, new_attacker = "", ""
            defender, new_defender = "", ""
            defenderReward, new_defenderReward = "", ""
            eta = ""
            new = []
            invasions = await get_all_data("invasions")
            for invasion in invasions:
                if not invasion['completed'] and invasion['eta'] != 'Infinityd':
                    new.append(invasion['id'])
                    node += invasion['node'] + "\n"
                    attackerReward += invasion['attackerReward']['asString'] + "\n" if not invasion[
                                                                                               'attackingFaction'] == 'Infested' else "N/A \n"
                    attacker += invasion['attackingFaction'] + "\n"
                    defender += invasion['defendingFaction'] + "\n"
                    defenderReward += (invasion['defenderReward']['asString'] + "\n")
                    eta += invasion['eta'] + "\n"

                    if invasion['id'] not in old:
                        new_node += invasion['node'] + "\n"
                        new_attackerReward += invasion['attackerReward']['asString'] + "\n" if not invasion[
                                                                                                       'attackingFaction'] == 'Infested' else "N/A \n"
                        new_attacker += invasion['attackingFaction'] + "\n"
                        new_defender += invasion['defendingFaction'] + "\n"
                        new_defenderReward += invasion['defenderReward']['asString'] + "\n"
            old = new

            for channel in ctx.guild.channels:
                if channel.name == "invasions":
                    correct_channel = channel

            if node != "":
                fembed = discord.Embed(
                    title=f'Alle Invasions:\n',
                    colour=discord.Colour.purple()
                )

                fembed.insert_field_at(0, name='Node               ', value=node, inline=True)
                fembed.insert_field_at(1, name='Attacker Reward           ', value=attackerReward, inline=True)
                fembed.insert_field_at(2, name='Attacker       ', value=attacker, inline=True)
                fembed.insert_field_at(3, name='Defender           ', value=defender, inline=True)
                fembed.insert_field_at(4, name='Defender Reward           ', value=defenderReward, inline=True)
                await correct_channel.send(embed=fembed)
            await asyncio.sleep(60)
        else:
            await correct_channel.send("The Invasion Check has been stopped.")
            print(f"Invasions Check for {ctx.guild.id} has been stopped.")


def calculate_remaining_world_duration(data):
    end = (datetime.strptime(data['expiry'], "%Y-%m-%dT%H:%M:%S.000Z") + timedelta(hours=1)).timetuple()
    temp_time = time.mktime(end) - time.mktime(time.localtime())
    h = 0
    m = temp_time / 60
    while m > 60:
        h += 1
        m -= 60
    s = temp_time % 60
    return int(h), int(m), int(s)


@bot.command()
async def cambion(ctx):
    df = await get_all_data("cambionCycle")
    h, m, s = calculate_remaining_world_duration(df)
    cycle = "Fass" if df['active'] == "fass" else "Vome"
    await ctx.channel.send(f"{ctx.author.mention}: Es ist {cycle}. Dauer: {h}:{m}:{s}.")


@bot.command()
async def cetus(ctx):
    df = await get_all_data("cetusCycle")
    h, m, s = calculate_remaining_world_duration(df)
    daynight = "Tag" if df['isDay'] else "Nacht"
    await ctx.channel.send(f"{ctx.author.mention}: Es ist {daynight} auf Cetus. Dauer: {h}:{m}:{s}.")


@bot.command()
async def vallis(ctx):
    df = await get_all_data("vallisCycle")
    warmcold = "warm" if df['isWarm'] else "kalt"
    await ctx.channel.send(f"{ctx.author.mention}: Es ist ziemlich {warmcold}. Für noch {df['timeLeft']}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def sortie(ctx):
    df = await get_all_data("sortie")
    s = df['variants']
    mission, node, modifier = "", "", ""

    for sorties in s:
        mission += f"{sorties['missionType']}\n"
        node += f"{sorties['node']}\n"
        modifier += f"{sorties['modifier']}\n"

    fembed = discord.Embed(
        title=f'Die Sortie für heute:\n',
        colour=discord.Colour.purple()
    )

    fembed.add_field(name='Mission Type       ', value=mission, inline=True)
    fembed.add_field(name='Node               ', value=node, inline=True)
    fembed.add_field(name='Modifier           ', value=modifier, inline=True)
    await ctx.send(embed=fembed)


@bot.command()
async def fissurecheck(ctx):
    role = discord.utils.get(ctx.guild.roles, name='Admin')
    if role in ctx.author.roles:
        if ctx.guild.id not in servers:
            servers[ctx.guild.id] = VariablesForChecks()
        servers[ctx.guild.id].fissure_check_started = not servers[ctx.guild.id].fissure_check_started
        await fissure_check(ctx)
    else:
        await ctx.channel.send("Du hast keine Berechtigung den Fissure Check zu starten")


@bot.command()
async def eidoloncheck(ctx):
    role = discord.utils.get(ctx.guild.roles, name='Eidolon')
    if role in ctx.author.roles:
        if ctx.guild.id not in servers:
            servers[ctx.guild.id] = VariablesForChecks()
        servers[ctx.guild.id].eidolon_check_started = not servers[ctx.guild.id].eidolon_check_started
        await eidolon_check(ctx)
    else:
        await ctx.channel.send("Du hast keine Berechtigung den Eidolon Check zu starten")


@bot.command()
async def fissures(ctx):
	channel = ctx.channel
    fembed = discord.Embed(
        title='Aktive Risse',
        colour=discord.Colour.green()
    )
    df = await get_all_data('fissures')
    tier, node, mission = "", "", ""
    for relic in ["Lith", "Meso", "Neo", "Axi", "Requiem"]:
        fissures = [item for item in df if item['tier'] == relic]
        for fissure in fissures:
            tier += fissure['tier'] + "\n"
            node += fissure['node'] + "\n"
            mission += fissure['missionType'] + "\n"
        tier += "\n"
        node += "\n"
        mission += "\n"

    fembed.add_field(name='Tier       ', value=tier, inline=True)
    fembed.add_field(name='Node       ', value=node, inline=True)
    fembed.add_field(name='Mission Type', value=mission, inline=True)
    await channel.send(embed=fembed)
    await whisper_specific_members(ctx, "Fissures", message="", embed=fembed)


@bot.command()
async def invasionscheck(ctx):
    if ctx.guild.id in servers:
        servers[ctx.guild.id] = VariablesForChecks()
    servers[ctx.guild.id].invasions_check_started = not servers[ctx.guild.id].invasions_check_started
    await invasions_check(ctx)


@bot.command()
async def toggle(ctx, args=None):
    if args is None:
        await ctx.send("Please provide a server role (Example: $toggle Eidolons).")
    elif args == "Admin":
        await ctx.send("Nice try tho.")
    else:
        role = discord.utils.get(ctx.guild.roles, name=args)
        if role is None:
            await ctx.send("This role does not exist.")
        else:
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
                await ctx.send(f"The role '{args}' has been given to you.")
            else:
                await ctx.author.add_roles(role)
                await ctx.send(f"The role '{args}' has been taken from you.")


bot.run(TOKEN_ID)
