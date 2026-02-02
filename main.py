#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

from asyncio import wait_for, TimeoutError
from urllib.parse import quote_plus
from random import randint, choice
from datetime import datetime
from os import environ
from re import match
from gpytranslate import Translator
from simpleeval import simple_eval
from aiohttp import ClientSession
from discord.ext import commands
from discord import (
    app_commands,
    Intents,
    Game,
    Forbidden,
    Interaction,
    Member,
    Message
)
from wikipedia import (
    set_lang,
    summary,
    PageError,
    DisambiguationError
)
from orjson import loads

activity = Game(name="slava ReBRT")
intents = Intents.default()

intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, activity=activity)

api_status_url = "https://status.sekai.best/history/api"
markup = f"[api.sekai.best]({api_status_url})"
api_alive = f"{markup} says it is alive ^^"
api_dead = f"{markup} umer nahui :("
api_issue = f"{markup} issue"

@bot.event
async def on_message(message: Message) -> None:
    if message.author != bot.user:
        anti_you = "\u0430\u043d\u0442\u0438 \u044e"
        if anti_you in message.content.lower():
            emoji = "<a:halal_antiyou:1463296137174974587>"
            _ = await message.reply(content=emoji, mention_author=False)

@bot.tree.command(description="Flip a coin")
async def coin(ctx: Interaction) -> None:
    result = choice(("I can't stop winning", "Oh dang it"))
    await reply(ctx, result)

@bot.tree.command(description="Pick a random item of all items")
@app_commands.describe(items="Set the space separated items list")
async def pick(ctx: Interaction, items: str) -> None:
    result = choice(items.split())
    await reply(ctx, result)

@bot.tree.command(description="I'm feeling lucky")
@app_commands.describe(
    text="Set the text to search",
    language="Set the search language, like en or ja"
)
async def google_search(
    ctx: Interaction,
    text: str,
    language: str = "ru"
) -> None:
    query = quote_plus(text)
    result = f"https://www.google.com/search?btnI=1&hl={language}&q={query}"
    await reply(ctx, result)

@bot.tree.command(description="Get the sekai leaderboard")
@app_commands.choices(
    type=[
        app_commands.Choice(name="not a WL", value="live"),
        app_commands.Choice(name="WL", value="live_latest_chapter")
    ],
    region=[
        app_commands.Choice(name="Global", value="en"),
        app_commands.Choice(name="Korea", value="kr"),
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="Taiwan", value="tw"),
        app_commands.Choice(name="China", value="cn")
    ],
    page=[
        app_commands.Choice(name="Page 1 (t1-t50)", value=1),
        app_commands.Choice(name="Page 2 (t50-t100)", value=2),
        app_commands.Choice(name="Page 3 (t100+)", value=3)
    ]
)
@app_commands.describe(
    type="Set the event type, a WL or not",
    region="Set the server region",
    page="Set the leaderboard page"
)
async def leaderboard(
    ctx: Interaction,
    type: str = "live",
    region: str = "en",
    page: int = 2
) -> None:
    await defer(ctx)
    url = f"https://api.sekai.best/event/{type}?region={region}"
    response_text = await get_response(url)
    parsed = loads(response_text)
    if page == 1:
        tops = slice(0, 50)
    elif page == 2:
        tops = slice(49, 100)
    else:
        tops = slice(99, None)
    if parsed["status"] == "success":
        data = parsed["data"]["eventRankings"]
        if data:
            board = (
                Top(data[i]["rank"], data[i]["userName"], data[i]["score"])
                    for i in range(len(data))
            )
            leaderboard = tuple(sorted(board, key=lambda x: x.top))
            if leaderboard:
                result = (
                    "```\n"
                    f"{''.join(f'{i}' for i in leaderboard[tops])}"
                    "```"
                )
            else:
                result = api_issue
        else:
            result = api_issue
    elif parsed["message"] == "only world bloom event has chapter rankings":
        result = "0_o  **GODDAMN THERE IS NO WL HERE**"
    else:
        result = api_dead
    await reply(ctx, result, True)

@bot.tree.command(description="Check is api.sekai.best alive")
async def check_api(ctx: Interaction) -> None:
    url = "https://api.sekai.best/status"
    response_text = get_response(url)
    if response_text is None:
        result = api_dead
    else:
        result = api_alive
    await reply(ctx, result)

@bot.tree.command(description="Get a value for compare ISVs")
@app_commands.describe(
    leader_skill="Your team leader skill",
    team_skill="Your total team skill, including the leader"
)
async def isv(ctx, leader_skill: int, team_skill: int) -> None:
    result = leader_skill*4 + team_skill - 90
    await reply(ctx, result)

@bot.tree.command(description="Change the room code")
@app_commands.describe(new_code="Set a new code for the room")
async def rm_code(ctx: Interaction, new_code: str) -> None:
    result = await edit_room(ctx, new_code, "")
    await reply(ctx, result)

@bot.tree.command(description="Change a room's players")
@app_commands.describe(players="Set a room's players, [1-5] or f")
async def rm_players(ctx: Interaction, players: str) -> None:
    result = await edit_room(ctx, "", players)
    await reply(ctx, result)

@bot.tree.command(description="Close the room")
async def rm_close(ctx: Interaction) -> None:
    result = await edit_room(ctx, "xxxxx", "hui")
    await reply(ctx, result)

@bot.tree.command(description="Convert UTC to a discord timestamp")
@app_commands.choices(
    type=[
        app_commands.Choice(name="t (short time)", value="t"),
        app_commands.Choice(name="T (long time)", value="T"),
        app_commands.Choice(name="f (long date + short time)", value="f"),
        app_commands.Choice(name="F (very long)", value="F"),
        app_commands.Choice(name="R (relative)", value="R")
    ]
)
@app_commands.describe(
    year="Set the year, like 1941",
    month="Set the month, like 06",
    day="Set the day, like 22",
    hour="Set the hour, like 05",
    minute="Set the minute, like 55"
)
async def timestamp(
    ctx: Interaction,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    type: str
) -> None:
    date = datetime(year, month, day, hour, minute, 0)
    timestamp = int(date.timestamp())
    result = f"<t:{timestamp}:{type}>"
    await reply(ctx, result)

@bot.tree.command(description="Convert timezone")
@app_commands.describe(
    hour="Set the hour to conver, like 22",
    source_timezone="The source timezone, like +3 or -12",
    target_timezone="The target timezone"
)
async def convert_timezone(
    ctx: Interaction,
    hour: int,
    source_timezone: int,
    target_timezone: int
) -> None:
    converted = hour + (source_timezone - target_timezone)
    if converted > 24:
        result = f"{converted - 24} of the next day"
    elif converted < 0:
        result = f"{converted + 24} of the previous day"
    else:
        result = f"{converted} of the same day"
    await reply(ctx, result)

@bot.tree.command(description="Convert rgb to hex")
@app_commands.describe(
    red="Set red color value, like 51",
    green="Set the green color value, like 204",
    blue="Set the blue color value, like 187"
)
async def rgb_to_hex(
    ctx: Interaction,
    red: int,
    green: int,
    blue: int
) -> None:
    if check_rgb(red, green ,blue):
        result = "#{:02x}{:02x}{:02x}".format(red, green, blue)
    else:
        result = "Invalid rgb color"
    await reply(ctx, result)

@bot.tree.command(description="Convert hex to rgb")
@app_commands.describe(hex_color="Set the hex color, like #33ccbb")
async def hex_to_rgb(ctx: Interaction, hex_color: str) -> None:
    hex_color = hex_color.lstrip("#")
    if match(r"^[0-9a-fA-F]+$", hex):
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
        result = f"{red} {green} {blue}"
    else:
        result = "Invalid hex color"
    await reply(ctx, result)

@bot.tree.command(description="Send a question to guess")
@app_commands.choices(
    difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Hard", value="hard")
    ],
    category=[
        app_commands.Choice(name="General knowledge", value=9),
        app_commands.Choice(name="Books", value=10),
        app_commands.Choice(name="Film", value=11),
        app_commands.Choice(name="Music", value=12),
        app_commands.Choice(name="Musicals + theatres", value=13),
        app_commands.Choice(name="Television", value=14),
        app_commands.Choice(name="Video games", value=15),
        app_commands.Choice(name="Board games", value=16),
        app_commands.Choice(name="Science+nature", value=17),
        app_commands.Choice(name="Computers", value=18),
        app_commands.Choice(name="Mathematics", value=19),
        app_commands.Choice(name="Mythology", value=20),
        app_commands.Choice(name="Sports", value=21),
        app_commands.Choice(name="Geography", value=22),
        app_commands.Choice(name="History", value=23),
        app_commands.Choice(name="Politics", value=24),
        app_commands.Choice(name="Art", value=25),
        app_commands.Choice(name="Celebrities", value=26),
        app_commands.Choice(name="Animals", value=27),
        app_commands.Choice(name="Vehicles", value=28),
        app_commands.Choice(name="Comics", value=29),
        app_commands.Choice(name="Gadgets", value=30),
        app_commands.Choice(name="Anime + manga", value=31),
        app_commands.Choice(name="Cartoon + animations", value=32)
    ]
)
@app_commands.describe(
    difficulty="Set the difficulty level",
    category="Set the category of the question"
)
async def guess(
    ctx: Interaction,
    difficulty: str = "easy",
    category: int = 15
) -> None:
    await defer(ctx)
    url = ("https://opentdb.com/api.php?amount=1"
           f"&category={category}&difficulty={difficulty}")
    response_text = await get_response(url)
    parsed = loads(response_text)
    result = parsed["results"][0]["question"]
    await reply(ctx, result, True)

@bot.tree.command(description="Get the text lenght")
@app_commands.describe(text="Set the text to measure")
async def length(ctx: Interaction, text: str) -> None:
    result = len(text)
    await reply(ctx, result)

@bot.tree.command(description="Translate the text")
@app_commands.describe(text="Set the text for translation")
async def translate(ctx: Interaction, text: str, target_language: str) -> None:
    result = await translate_text(text[:2000], target_language)
    await reply(ctx, result)

@bot.tree.command(description="Translate the text into russian")
@app_commands.describe(text="Set the text for translation")
async def russian(ctx: Interaction, text: str) -> None:
    result = await translate(text_for_translation[:2000], "ru")
    await reply(ctx, result)

@bot.tree.command(description="Wikipedia search")
@app_commands.describe(
    text="Set the text to search",
    language="Set the search language, like en or ja"
)
async def wikipedia_search(
    ctx: Interaction,
    text: str,
    language: str = "ru"
) -> None:
    await defer(ctx)
    set_lang(language)
    try:
        wikitext = summary(text)
    except DisambiguationError as wiki_issue:
        random = choice(wiki_issue.options)
        wikitext = summary(random)
    except PageError:
        wikitext = "Not found"
    result = wikitext[:2000]
    await reply(ctx, result, True)

@bot.tree.command(description="calculator")
@app_commands.describe(expression="Set a math expression, like 2+2")
async def calculate(ctx: Interaction, expression: str) -> None:
    result = simple_eval(expression)
    await reply(ctx, result)

@bot.tree.command(description="Get the weather information")
@app_commands.describe(location="Set the location, like moskva")
async def weather(ctx: Interaction, location: str) -> None:
    await defer(ctx)
    url = f"https://wttr.in/{location}?format=%t+%C+%uuv+%T&m&lang=ru"
    result = await get_response(url)
    await reply(ctx, result, True)

@bot.tree.command(description="Repeat the text")
@app_commands.describe(
    text="Set the text for repeating",
    repeats="Set the repeating amount"
)
async def repeat(ctx: Interaction, text: str, repeats: int = 79) -> None:
    if repeats > 2000:
        result = "too many repeats"
    else:
        text = "".join(text for _ in range(repeats))
        result = text[:2000]
    await reply(ctx, result)

@bot.tree.command(description="Send a random number")
@app_commands.describe(
    start="Set the range start",
    stop="Set the range end"
)
async def random(ctx: Interaction, start: int = 1, stop: int = 100) -> None:
    result = randint(start, stop)
    await reply(ctx, result)

@bot.tree.command(description="Nene sleep emoji")
async def nene_sleep(ctx: Interaction) -> None:
    result = "<a:nene_sleep:1462809640017334293>"
    await reply(ctx, result)

@bot.tree.command(description="Cum emoji")
async def cum(ctx: Interaction) -> None:
    result = "<a:cum:1410053954494267485>"
    await reply(ctx, result)

@bot.tree.command(description="Make a QR code")
@app_commands.describe(text="Set the text for new QR code")
async def qr(ctx: Interaction, text: str) -> None:
    text = quote_plus(text, safe='')
    url = ("https://api.qrserver.com/v1/create-qr-code/?size=1000x1000"
           f"&qzone=4&data={text}")
    result = url[:2000]
    await reply(ctx, result)

@bot.tree.command(description="Hug a user <3")
@app_commands.describe(user="Set a user to hug")
async def hug(ctx: Interaction, user: Member) -> None:
    category = choice(("cuddle", "hug"))
    url = f"https://api.waifu.pics/sfw/{category}"
    response_text = await get_response(url)
    parsed = loads(response_text)
    img_url = parsed["url"]
    result = f"{user.mention}[))))]({img_url})  <3"
    await reply(ctx, result)

@bot.tree.command(description="Send a random categorized sfw image")
@app_commands.choices(
    category=[
        app_commands.Choice(name="Waifu", value="waifu"),
        app_commands.Choice(name="Neko", value="neko"),
        app_commands.Choice(name="Shinobu", value="shinobu"),
        app_commands.Choice(name="Megumin", value="megumin"),
        app_commands.Choice(name="Cuddle", value="cuddle"),
        app_commands.Choice(name="Cry", value="cry"),
        app_commands.Choice(name="Hug", value="hug"),
        app_commands.Choice(name="Kiss", value="kiss"),
        app_commands.Choice(name="Lick", value="lick"),
        app_commands.Choice(name="Pat", value="pat"),
        app_commands.Choice(name="Smug", value="smug"),
        app_commands.Choice(name="Bonk", value="bonk"),
        app_commands.Choice(name="Yeet", value="yeet"),
        app_commands.Choice(name="Blush", value="blush"),
        app_commands.Choice(name="Smile", value="smile"),
        app_commands.Choice(name="Wave", value="wave"),
        app_commands.Choice(name="Nom", value="nom"),
        app_commands.Choice(name="Bite", value="bite"),
        app_commands.Choice(name="Glomp", value="glomp"),
        app_commands.Choice(name="Slap", value="slap"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Wink", value="wink"),
        app_commands.Choice(name="Poke", value="poke"),
        app_commands.Choice(name="Dance", value="dance"),
        app_commands.Choice(name="Cringe", value="cringe")
    ]
)
@app_commands.describe(category="Set the image category")
async def sfw_categorized(ctx: Interaction, category: str) -> None:
    url = f"https://api.waifu.pics/sfw/{category}"
    response_text = await get_response(url)
    parsed = loads(response_text)
    result = parsed["url"]
    await reply(ctx, result)

@bot.tree.command(description="Send a random categorized nsfw image")
@app_commands.choices(
    category=[
        app_commands.Choice(name="Waifu", value="waifu"),
        app_commands.Choice(name="Neko", value="neko"),
        app_commands.Choice(name="Trap", value="trap"),
        app_commands.Choice(name="Blowjob", value="blowjob"),
        app_commands.Choice(name="Random", value="random")
    ]
)
@app_commands.describe(category="Set the image category")
async def nsfw_categorized(ctx: Interaction, category: str) -> None:
    if ctx.channel.is_nsfw():
        if category == "random":
            categories = ("waifu", "neko", "trap", "blowjob")
            category = choice(categories)
        url = f"https://api.waifu.pics/nsfw/{category}"
        response_text = await get_response(url)
        parsed = loads(response_text)
        result = parsed["url"]
    else:
        result = "This channel is not nsfw, ne eshkere :("
    await reply(ctx, result)

@bot.tree.command(description="Send a random sfw image")
async def sfw(ctx: Interaction) -> None:
    url = ("https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1"
           "&limit=1&random=true")
    response_text = await get_response(url)
    parsed = loads(response_text)
    img_url = parsed[0]["file_url"]
    result = img_url.lstrip("\\")
    await reply(ctx, result)

@bot.tree.command(description="Sync the commands to discord")
async def sync(ctx: Interaction) -> None:
    owner = await bot.is_owner(ctx.user)
    if owner:
        synced = len(await bot.tree.sync())
        result = f"Synced {synced} commands, goida"
    else:
        result = "Not enough swaga to do this"
    await reply(ctx, result)

@bot.tree.command(description="Check is the bot alive")
async def check_bot(ctx: Interaction) -> None:
    result = "slava ReBRT"
    await reply(ctx, result)

class Top:
    """A leaderboard unit."""
    def __init__(self, top: int, user_name: str, score: int):
        self.top = top
        self.user_name = user_name
        self.score = score

    def __str__(self) -> str:
        return (f"{self.top} '{self.user_name[slice(20)]}'"
                f" {'{0:,}'.format(self.score)}\n")

async def edit_room(
    ctx: Interaction,
    new_code: str,
    new_players: str
) -> str:
    channel = ctx.channel
    channel_regex = r"^(.*-)([0-9x]{5})(-[1-5f])?$"
    regex_match = match(channel_regex, channel.name)
    if match:
        prefix = regex_match.group(1)
        old_code = regex_match.group(2)
        old_suffix = regex_match.group(3) or ""
        final_code = new_code if new_code else old_code
        if new_players:
            final_suffix = "" if new_players == "hui" else f"-{new_players}"
        else:
            final_suffix = old_suffix
        new_name = f"{prefix}{final_code}{final_suffix}"
        if match(channel_regex, new_name):
            try:
                result = f"~~{channel.name}~~ -> `{new_name}`\n*Goida!*"
                _ = await wait_for(channel.edit(name=new_name), timeout=2)
            except TimeoutError:
                result = (
                    f"New room code: **{new_name}**\n"
                    "*2 channel name edits per 10 minutes limit reached*"
                )
            except Forbidden:
                result = "U menya net prav"
        else:
            result = f"Invalid new channel name: {new_name}"
    else:
        result = "The channel name is invalid"
    return result

async def check_rgb(red: int, green: int, blue: int) -> bool:
    values = (red, green, blue)
    result = all(0 <= value <= 255 for value in values)
    return result

async def get_response(url: str) -> str:
    headers = ({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/100.0.4896.127 Safari/537.36"})
    async with ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()

async def translate_text(text: str, target_language: str) -> str:
    async with Translator() as translator:
        result = await translator.translate(text[:2000],
                                            targetlang=target_language)
        return result

async def defer(ctx: Interaction) -> None:
    """Wait longer for a reply."""
    _ = await ctx.response.defer()

async def reply(
    ctx: Interaction,
    result: str | int,
    defer: bool = False
) -> None:
    """Send the result."""
    if result == "":
        result = "Error hz"
    if defer:
        _ = await ctx.followup.send(result)
    else:
        _ = await ctx.response.send_message(result)

bot.run(environ["TOKEN"])
