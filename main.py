#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""A discord bot."""

from asyncio import wait_for, TimeoutError
from re import compile, match
from random import choice
from os import environ
from gpytranslate import Translator
from simpleeval import simple_eval
from aiohttp import ClientSession
from orjson import loads
from discord import (
    app_commands,
    Intents,
    Client,
    Interaction,
    TextChannel,
    ClientUser,
    Message,
    Member,
    Forbidden
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127"
    " Safari/537.36"
}
MANAGER_ROLES = {
    1470549658454458471: "Раннер ростера",
    1316002183895973979: "Менеджер",
    1316002661895508058: "Интерн"
}
MAX_MESSAGE_LEN = 2000
CHANNEL_NAME_REGEX = compile(r"(^.[0-9]*-)[0-9x]{5}(-[1-5])?$", flags=0)
SEKAI_CODE_REGEX = compile(r"^[0-9x]{5}$", flags=0)
translator = Translator()

class GoidaBot(Client):
    user: ClientUser
    def __init__(self) -> None:
        intents = Intents.default()
        intents.message_content = True
        super().__init__(
            intents=intents,
            help_command=None,
            chunk_guilds_at_startup=False)
        self.tree = app_commands.CommandTree(self)
        self.session: ClientSession = None

    async def setup_hook(self) -> None:
        await self.tree.sync()
        self.session = ClientSession()

    async def close(self) -> None:
        await super().close()
        if self.session:
            await self.session.close()

    async def on_message(self, message: Message) -> None:
        author = message.author
        if author.id != self.user.id:
            message_text = message.content
            if (
                SEKAI_CODE_REGEX.match(message_text)
                and any(role.id in MANAGER_ROLES for role in author.roles)
            ):
                channel = message.channel
                channel_name = channel.name
                channel_match = CHANNEL_NAME_REGEX.match(channel_name)
                if channel_match:
                    prefix = channel_match.group(1)
                    new_name = prefix + message_text
                    try:
                        content = (
                            f"~~{channel_name}~~ -> **`{new_name}`**"
                            "\n*Гойда!*"
                        )
                        reason = "старый код румы был депнут в казик"
                        await wait_for(
                            channel.edit(name=new_name, reason=reason),
                            timeout=2)
                    except TimeoutError:
                        content = (
                            f"Новый код румы: **`{new_name}`**"
                            "\nЮзни `%rm code` чтобы сменить название канала"
                        )
                    except Forbidden:
                        content = "**У меня нет прав** на управление каналами"
                    await message.reply(content=content, mention_author=False)

bot = GoidaBot()

@bot.tree.context_menu(name="Translate into English")
async def translate_into_english(ctx: Interaction, message: Message):
    await ctx.response.defer(ephemeral=True)
    result = await translate(message.content, "en")
    await reply(ctx, result, True)

@bot.tree.context_menu(name="Перевести на русский")
async def translate_into_russian(ctx: Interaction, message: Message):
    await ctx.response.defer(ephemeral=True)
    result = await translate(message.content, "ru")
    await reply(ctx, result, True)

@bot.tree.command(description="Выбрать рандомный элемент списка")
@app_commands.describe(items="Разделенный пробелами список")
async def pick(ctx: Interaction, items: str) -> None:
    result = choice(items.split())
    await reply(ctx, result)

@bot.tree.command(description="Посчитать значение чтобы сравнить ISV")
@app_commands.describe(
    leader_boost="Скор буст лидера",
    team_boost="Суммарный скор буст тимы"
)
async def isv(ctx: Interaction, leader_boost: int, team_boost: int) -> None:
    result = leader_boost*4 + team_boost - 90
    await reply(ctx, result)

@bot.tree.command(description="Найти discord id чела")
@app_commands.describe(
    guy="Чел"
)
async def guy_id(ctx: Interaction, guy: Member) -> None:
    result = guy.id
    await reply(ctx, result)

@bot.tree.command(description="Найти ориг ник чела")
@app_commands.describe(
    guy="Чел"
)
async def guy_name(ctx: Interaction, guy: Member) -> None:
    name = guy.global_name
    result = name if name else "_Чел без ника"
    await reply(ctx, result)

@bot.tree.command(description="Найти аву чела")
@app_commands.describe(
    guy="Чел"
)
async def guy_avatar(ctx: Interaction, guy: Member) -> None:
    avatar = guy.avatar
    result = avatar if avatar else "Безавный зверь"
    await reply(ctx, result)

@bot.tree.command(description="Конвертировать rgb в hex")
@app_commands.describe(
    red="Красный",
    green="Зеленый",
    blue="Синий"
)
async def rgb_to_hex(
    ctx: Interaction,
    red: int,
    green: int,
    blue: int
) -> None:
    if await check_rgb(red, green, blue):
        result = f"#{red:02x}{green:02x}{blue:02x}"
    else:
        result = "Нормальный rgb вводи"
    await reply(ctx, result)

@bot.tree.command(description="Записать hex в rgb")
@app_commands.describe(hex_color="Цвет в hex, например #33ccbb")
async def hex_to_rgb(ctx: Interaction, hex_color: str) -> None:
    hex_color = hex_color.lstrip("#")
    if match(r"^[0-9a-fA-F]+$", hex_color):
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
        result = f"{red} {green} {blue}"
    else:
        result = "Нормальный hex вводи"
    await reply(ctx, result)

@bot.tree.command(description="Посчитать длину строки")
@app_commands.describe(text="Пиши свою строку")
async def length(ctx: Interaction, text: str) -> None:
    result = len(text)
    await reply(ctx, result)

@bot.tree.command(description="Калькулятор")
@app_commands.describe(expression="Напиши выражение, типа 2 + 2")
async def calculate(ctx: Interaction, expression: str) -> None:
    result = simple_eval(expression.replace(",", ""))
    await reply(ctx, result)

@bot.tree.command(description="Написать погоду")
@app_commands.describe(location="Город, moskva например")
async def weather(ctx: Interaction, location: str) -> None:
    await ctx.response.defer()
    url = f"https://wttr.in/{location}?format=%t+%C+%uuv+%T&m&lang=ru"
    result = await get_response(url)
    await reply(ctx, result, True)

@bot.tree.command(description="Проверить жив ли бот")
async def check_bot(ctx: Interaction) -> None:
    result = "ГОЙДА"
    await reply(ctx, result)

async def check_rgb(red: int, green: int, blue: int) -> bool:
    values = (red, green, blue)
    result = all(0 <= value <= 255 for value in values)
    return result

async def get_response(url: str) -> str:
    async with bot.session.get(url, headers=HEADERS) as response:
        return await response.text()

async def translate(text: str, target_language: str) -> str:
    translation = await translator.translate(
        text[:MAX_MESSAGE_LEN],
        targetlang=target_language)
    result = translation.text
    return result

async def reply(
    ctx: Interaction,
    result: str | int | float,
    defer: bool = False,
    silent: bool = False
) -> None:
    """Send the result."""
    if defer:
        await ctx.followup.send(result, silent=silent)
    else:
        await ctx.response.send_message(result, silent=silent)

bot.run(environ["TOKEN"])
