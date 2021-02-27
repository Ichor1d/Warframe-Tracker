# TODO: Split the bot into: Commands & Function.
# Also make specific send-functions in order to allow functions to be only the function itself - not the
# one sending the message. Also this might help reduce code.
# Also: Clean up the mess. Sort functions by what they do and what they are needed for
# Change checks to be only started by "Admins"

import discord
import asyncio
import aiohttp
import os
from discord.ext import commands
from discord.ext.commands import bot
from datetime import datetime, timedelta
import time

intents = discord.Intents.default()
intents.members = True
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix='$', intents=intents)
bot.remove_command("help")

servers = {}
helpEmbed = discord.Embed()

# nested_eidolon_users = {ctx.guild.id_1 : { user.id_1: {USER}, ... }, ... }
#                         ctx.guild.id_2 : { user.id_1: {USER}, user.id_2: {USER}} ... }
nested_eidolon_users = {}

# nested_fissure_users = {ctx.guild.id_1 : { user.id_1: {USER}, user.id_2: {USER}, ... },
#                         ctx.guild.id_2 : { user.id_1: {USER}, user.id_2: {USER}} ... }
nested_fissure_users = {}

# nested_invasion_users = {ctx.guild.id_1 : { detonite: { user.id: { USER }, ... }, ...},
#                           ctx.guild.id_2 : { fieldron: { user.id : { USER }, ... }, ...}}
nested_invasion_users = {}
nested_invasion_user_generell = {}


class VariablesForChecks:
    def __init__(self):
        self.fissure_check_started = False
        self.eidolon_check_started = False
        self.invasions_check_started = False


# TODO: Write a function for people to sign up to specific whispering.
async def whisper_invasion_subscribers(ctx: commands.context, message: str = "", embed: discord.embeds = None):
    guild = ctx.guild.id
    if guild in nested_invasion_users:
        for member in nested_invasion_users[guild]:
            if not member.bot:
                if embed is None:
                    await member.send(message)
                elif message is "":
                    await member.send(embed=embed)
    pass


async def whisper_fissure_subscribers(ctx: commands.context, message: str = "", embed: discord.embeds = None):
    guild = ctx.guild.id
    if guild in nested_fissure_users:
        for member in nested_fissure_users[guild]:
            if not member.bot:
                if embed is None:
                    await member.send(message)
                elif message is "":
                    await member.send(embed=embed)
    pass


# TODO: Write a function to whisper members with a specific role and only if they want to!
async def whisper_specific_members(ctx: commands.context, specific_role: str, message="", embed=None):
    tmp = [member for member in ctx.guild.members if
           discord.utils.get(ctx.guild.roles, name=specific_role) in member.roles]
    for member in tmp:
        if member != bot.user:
            if embed is None:
                await member.send(message)
            elif message is "":
                await member.send(embed=embed)


async def create_fissure_embed(ctx: commands.context, tier: str, node: str, mission: str):
    correct_channel = ctx.channel
    for channel in ctx.guild.channels:
        if channel.name == "fissures":
            correct_channel = channel
    fembed = discord.Embed(
        title='Neue Risse',
        colour=discord.Colour.dark_purple()
    )

    fembed.add_field(name='Tier       ', value=tier, inline=True)
    fembed.add_field(name='Node       ', value=node, inline=True)
    fembed.add_field(name='Mission Type', value=mission, inline=True)
    await correct_channel.send(embed=fembed)
    await whisper_fissure_subscribers(ctx, embed=fembed)


async def get_all_data(url: str = None):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.warframestat.us/pc/{url}") as r:
            if r.status == 200:
                return await r.json()
        await session.close()


async def eidolon_check(ctx: commands.context):
    channel = bot.get_channel(812422704719593513)
    if not servers[ctx.ctx.guild.id].eidolon_check_started:
        await channel.send("Beendigung des Eidolon Checks.")
    else:
        wd = await get_all_data("cetusCycle")
        isDay = wd['isDay']
        h, m, s = calculate_remaining_world_duration(wd)
        timeRemaining = ((h * 60) + m) * 60 + s

        await channel.send("Starting eidolon check.")
        while servers[ctx.ctx.guild.id].eidolon_check_started:
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


async def fissure_check(ctx: commands.context):
    correct_channel = ctx.channel
    for channel in ctx.guild.channels:
        if channel.name == "fissures":
            correct_channel = channel
    if not servers[ctx.guild.id].fissure_check_started:
        await correct_channel.send("Beendigung des Fissure Checks!")
    else:
        await correct_channel.send("Starting Fissure Check now. Checking every 5min")
        old = await get_all_data("fissures")
        old_ids = []
        for iterator in old:
            old_ids.append(iterator['id'])

        while servers[ctx.guild.id].fissure_check_started:
            new = await get_all_data("fissures")
            new_ids = []
            tier = ""
            node = ""
            mission = ""
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


@bot.command(pass_context=True)
async def invasion_status(ctx):
    invasions = await get_all_data("invasions")

    for invasion in invasions:
        if not invasion['completed'] and invasion['eta'] != 'Infinityd':
            teststr = f"{invasion['node']}\n"
            com = int(invasion['completion'])
            com = com/2
            for i in range(int(com)):
                teststr += "0"
            teststr += " "
            for i in range(int(com), 49):
                teststr += "O"
            teststr += "]"
            await ctx.send("```ml\n" + teststr + "```")


async def invasions_check(ctx: commands.context):
    old = []
    # look for the channel "invasions" otherwise use the channel, where the command has been set up
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
                    attackerReward += invasion['attackerReward']['asString'] + "\n" \
                        if not invasion['attackingFaction'] == 'Infested' else "N/A \n"
                    attacker += invasion['attackingFaction'] + "\n"
                    defender += invasion['defendingFaction'] + "\n"
                    defenderReward += (invasion['defenderReward']['asString'] + "\n")
                    eta += invasion['eta'] + "\n"

                    if invasion['id'] not in old:
                        new_node += invasion['node'] + "\n"
                        new_attackerReward += invasion['attackerReward']['asString'] + "\n" \
                            if not invasion['attackingFaction'] == 'Infested' else "N/A \n"
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
                await whisper_invasion_subscribers(ctx, embed=fembed)
            await asyncio.sleep(60)
        else:
            await correct_channel.send("The Invasion Check has been stopped.")
            print(f"Invasions Check for {ctx.guild.id} has been stopped.")


def calculate_remaining_world_duration(data: dict):
    end = (datetime.strptime(data['expiry'], "%Y-%m-%dT%H:%M:%S.000Z") + timedelta(hours=1)).timetuple()
    temp_time = time.mktime(end) - time.mktime(time.localtime())
    h = 0
    m = temp_time / 60
    while m > 60:
        h += 1
        m -= 60
    s = temp_time % 60
    return int(h), int(m), int(s)


@bot.command(pass_context=True)
async def cambion(ctx: commands.context):
    df = await get_all_data("cambionCycle")
    h, m, s = calculate_remaining_world_duration(df)
    cycle = "Fass" if df['active'] == "fass" else "Vome"
    await ctx.channel.send(f"{ctx.author.mention}: Es ist {cycle}. Dauer: {h}:{m}:{s}.")


@bot.command(pass_context=True)
async def cetus(ctx: commands.context):
    df = await get_all_data("cetusCycle")
    h, m, s = calculate_remaining_world_duration(df)
    daynight = "Tag" if df['isDay'] else "Nacht"
    await ctx.channel.send(f"{ctx.author.mention}: Es ist {daynight} auf Cetus. Dauer: {h}:{m}:{s}.")


@bot.command(pass_context=True)
async def vallis(ctx: commands.context):
    df = await get_all_data("vallisCycle")
    warmcold = "warm" if df['isWarm'] else "kalt"
    await ctx.channel.send(f"{ctx.author.mention}: Es ist ziemlich {warmcold}. Für noch {df['timeLeft']}")


@bot.command(pass_context=True)
async def sortie(ctx: commands.context):
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


@bot.command(pass_context=True)
async def fissures(ctx: commands.context):
    channel = ctx.channel

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

    fembed = discord.Embed(
        title='Active Fissures',
        colour=discord.Colour.green()
    )

    fembed.add_field(name='Tier       ', value=tier, inline=True)
    fembed.add_field(name='Node       ', value=node, inline=True)
    fembed.add_field(name='Mission Type', value=mission, inline=True)
    await channel.send(embed=fembed)
    await whisper_specific_members(ctx, "Fissures", message="", embed=fembed)


@bot.command(pass_context=True)
async def invasionscheck(ctx: commands.context):
    if ctx.guild.id not in servers:
        servers[ctx.guild.id] = VariablesForChecks()
    servers[ctx.guild.id].invasions_check_started = not servers[ctx.guild.id].invasions_check_started
    await invasions_check(ctx)


@bot.command(pass_context=True)
async def fissurecheck(ctx: commands.context):
    role = discord.utils.get(ctx.guild.roles, name='Admin')
    if role in ctx.author.roles:
        if ctx.guild.id not in servers:
            servers[ctx.guild.id] = VariablesForChecks()
        servers[ctx.guild.id].fissure_check_started = not servers[ctx.guild.id].fissure_check_started
        await fissure_check(ctx)
    else:
        await ctx.channel.send("Du hast keine Berechtigung den Fissure Check zu starten")


@bot.command(pass_context=True)
async def eidoloncheck(ctx: commands.context):
    role = discord.utils.get(ctx.guild.roles, name='Eidolon')
    if role in ctx.author.roles:
        if ctx.guild.id not in servers:
            servers[ctx.guild.id] = VariablesForChecks()
        servers[ctx.guild.id].eidolon_check_started = not servers[ctx.guild.id].eidolon_check_started
        await eidolon_check(ctx)
    else:
        await ctx.channel.send("Du hast keine Berechtigung den Eidolon Check zu starten")


@bot.command(pass_context=True)
async def toggle(ctx: commands.context, args=""):
    if args == "":
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


@bot.command(pass_context=True)
async def subscribe(ctx: commands.context, args: str = ""):
    guild = ctx.guild.id
    user = ctx.message.author
    role = args.lower()

    if role == 'eidolon':
        if guild not in nested_eidolon_users:
            nested_eidolon_users[guild] = {}
        if user not in nested_eidolon_users[guild]:
            nested_eidolon_users[guild][user] = user
            await ctx.channel.send(f"{ctx.message.author} has been added to the subscription list for Eidolons")
        else:
            del nested_eidolon_users[guild][user]
            await ctx.channel.send(f"{ctx.message.author} has been removed from the subscription list for Eidolons")
    elif role == 'fissures':
        if guild not in nested_fissure_users:
            nested_fissure_users[guild] = {}
        if user not in nested_fissure_users[guild]:
            nested_fissure_users[guild][user] = user
            await ctx.channel.send(f"{ctx.message.author} has been added to the subscription list for Fissures")
        else:
            del nested_fissure_users[guild][user]
            await ctx.channel.send(f"{ctx.message.author} has been removed from the subscription list for Fissures")
    elif role == 'invasions':
        if guild not in nested_invasion_user_generell:
            nested_invasion_user_generell[guild] = {}
            await ctx.channel.send(f"{ctx.message.author} has been added to the subscription list for Invasions")
        if user not in nested_invasion_user_generell[guild]:
            nested_invasion_user_generell[guild][user] = user
        else:
            del nested_invasion_user_generell[guild][user]
            await ctx.channel.send(f"{ctx.message.author} has been removed from the subscription list for Invasions")
    elif role == 'detonite':
        if guild not in nested_invasion_users:
            nested_invasion_users[guild] = {}
            nested_invasion_users[guild]['detonite'] = {}
        if user not in nested_invasion_users[guild]['detonite']:
            nested_invasion_users[guild]['detonite'][user] = user
            await ctx.channel.send(f"{ctx.message.author} has been added to the subscription list for Detonite")
        else:
            del nested_invasion_users[guild]['detonite'][user]
            await ctx.channel.send(f"{ctx.message.author} has been removed from the subscription list for Detonite")
    elif role == 'fieldron':
        if guild not in nested_invasion_users:
            nested_invasion_users[guild] = {}
            nested_invasion_users[guild]['fieldron'] = {}
        if user not in nested_invasion_users[guild]['fieldron']:
            nested_invasion_users[guild]['fieldron'][user] = user
            await ctx.channel.send(f"{ctx.message.author} has been added to the subscription list for Fieldron")
        else:
            del nested_invasion_users[guild]['Fieldron'][user]
            await ctx.channel.send(f"{ctx.message.author} has been removed from the subscription list for Fieldron")
    elif role == 'mutagen':
        if guild not in nested_invasion_users:
            nested_invasion_users[guild] = {}
            nested_invasion_users[guild]['mutagen'] = {}
        if user not in nested_invasion_users[guild]['mutagen']:
            nested_invasion_users[guild]['mutagen'][user] = user
            await ctx.channel.send(f"{ctx.message.author} has been added to the subscription list for Mutagen Mass")
        else:
            del nested_invasion_users[guild]['mutagen'][user]
            await ctx.channel.send(f"{ctx.message.author} has been removed from the subscription list for Mutagen Mass")
    elif role == 'weapon':
        if guild not in nested_invasion_users:
            nested_invasion_users[guild] = {}
            nested_invasion_users[guild]['weapon'] = {}
        if user not in nested_invasion_users[guild]['weapon']:
            nested_invasion_users[guild]['weapon'][user] = user
        else:
            del nested_invasion_users[guild]['Weapon'][user]
    elif role == 'potato':
        if guild not in nested_invasion_users:
            nested_invasion_users[guild] = {}
            nested_invasion_users[guild]['potato'] = {}
        if user not in nested_invasion_users[guild]['potato']:
            nested_invasion_users[guild]['potato'][user] = user
        else:
            del nested_invasion_users[guild]['potato'][user]
    else:
        ctx.channel.send("This Subscriptionlist does not exist.")
    pass


@bot.command(pass_context=True)
async def help(ctx, args=None):
    if args is None:
        await ctx.channel.send(embed=helpEmbed)
    else:
        fembed = discord.Embed(
            title=f'help for ${args}',
            colour=discord.Colour.green()
        )

        arguments = {
            'invasioncheck': 'This command is only accepted, when setup by someone with the role Admin.\n'
                             'Turns on or off the check for new Invasions every minute. If a new Invasion comes up '
                             'the bot will whisper every subscribed member and send a message in the channel'
                             ' "invasion". If there is no channel "invasion" it will '
                             'send the message in the channel the command has been send.\n'
                             'If you receive unwanted messages please use the subscribe command.',
            'fissurecheck': 'This command is only accepted, when setup by someone with the role Admin.\n'
                            'Turns on or off the check for new Fissures every minute. If a new Fissure comes up '
                            'the bot will whisper every subscribed member and send a message in the channel "fissures".'
                            '\nIf there is no channel "fissures" it will send the message in the channel the '
                            'command has been send.\n'
                            'If you receive unwanted messages please use the subscribe command.',
            'eidoloncheck': 'This command is only accepted, when setup by someone with the role Admin.\n'
                            'Whenever night on Cetus comes up the bot will whisper every subscribed member '
                            'and send a message in the channel "eidolon".\n'
                            'If there is no channel "eidolon" it will send the message in the channel the'
                            ' command has been send.\n'
                            ' If you receive unwanted messages please use the subscribe command.',
            'toggle': 'You need to mention a role, when you send this command and the bot will give you that role.\n'
                      'This will *not* subscribe you to the list of fissures, invasions or nighttime on Cetus.\n'
                      'e.g: $toggle fissures.',
            'subscribe': 'Lets you subscribe to the list of certain checks. If you are subscribed to the checks the bot'
                         ' will whisper you as soon as the bot has news. Possible options are:\n'
                         'invasions - will mesage you on EVERY new invasions.\n'
                         'fieldron - will message you when a new invasion with Fieldron comes up\n'
                         'detonite - will message you when a new invasion with Detonite comes up\n'
                         'mutagen - will mesage you when a new invasion with Mutagen Mass comes up\n'
                         'weapon - will message you when a new invasion with a Wraith/Vandal weapon comes up\n'
                         'potato - will message you when a new invasion with a Potato comes up\n'
                         'fissures - will message you when a new fissure opens\n'
                         'eidolon - will mesage you, when night on Cetus comes.\n',
        }
        if args in arguments:
            fembed.add_field(name=f"${args}", value=arguments[args])
            await ctx.send(embed=fembed)
        else:
            await ctx.send("No more information for this command or unknown command.")


@bot.event
async def on_ready():
    global helpEmbed
    hembed = discord.Embed(
        title='All commands',
        colour=discord.Colour.dark_purple()
    )

    status = "$vallis - shows the world status of Orb Vallis\n" \
             "$cambion - shows the world status of the Cambion Drift\n" \
             "$cetus - shows the world status of Cetus\n" \
             "$sortie - gives you the todays sortie\n" \
             "$fissures - shows all current fissures"

    checks = "$invasioncheck - toggles the check for new invasions on/off\n" \
             "$fissurecheck - toggles the check for new fissures on/off\n" \
             "$eidoloncheck - toggles the check for night on Cetus on/off"

    utility = "$toggle - gives/removes you the mentioned role\n" \
              "$subscribe - lets you un-/subscribe to the different checks"

    hembed.add_field(name='Status', value=status, inline=False)
    hembed.add_field(name='Checks', value=checks, inline=False)
    hembed.add_field(name='Utility', value=utility, inline=False)
    hembed.set_footer(text="Write $help [command] for more information on a specific command.")
    helpEmbed = hembed
    print(f"Logged in as {bot.user}")


TOKEN_ID = os.environ['TOKEN_ID']
bot.run(TOKEN_ID)
