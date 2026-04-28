#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""A discord bot."""

from datetime import datetime
from asyncio import wait_for, sleep
from random import random
from os import environ
from gpytranslate import Translator, TranslationError
from discord.abc import Messageable
from uvloop import install
from discord import (
    app_commands,
    Intents,
    Client,
    Game,
    Interaction,
    TextChannel,
    ClientUser,
    Message,
    Member,
    Forbidden
)
import simpleeval

class GoidaBot(Client):
    user: ClientUser
    def __init__(self) -> None:
        activity = Game("Форсакен")
        intents = Intents.default()
        intents.message_content = True
        super().__init__(
            intents=intents,
            activity=activity,
            chunk_guilds_at_startup=False)
        self.tree = app_commands.CommandTree(self)
        self.sync_enabled = environ["BOT_SYNC_ENABLED"]
        self.start_time = datetime.now()
        self.max_message_len = 2000
        self.channel_name_len = 8
        self.sekai_code_len = 5
        self.room_letter = "g"
        self.manager_roles = {
            "Раннер ростера",
            "Лид-менеджер",
            "Менеджер",
            "Интерн"
        }

    async def setup_hook(self) -> None:
        if self.sync_enabled == "1":
            await self.tree.sync()

    async def on_message(self, message: Message) -> None:
        """Highlight the sekai room code."""
        sleep(random())
        channel = message.channel
        author = message.author
        if not is_human_in_text_channel(author, channel):
            return
        message_text = message.content
        if not is_sekai_code(message_text):
            return
        channel_name = channel.name
        old_code = channel_name[-bot.sekai_code_len:]
        if message_text == old_code:
            return
        room_prefix = get_room_prefix(channel_name)
        if not room_prefix:
            return
        if not is_manager(author):
            return
        content = f"~~{old_code}~~ → **`{message_text}`**"
        try:
            reason = "старый код румы был депнут в казик"
            name = room_prefix + message_text
            await wait_for(channel.edit(name=name, reason=reason), timeout=2.0)
        except TimeoutError:
            content = f"Новый код румы: **`{message_text}`**\n> Юзни `%rm`"
        except Forbidden:
            content = "**У меня нет прав** на управление каналами"
        await message.reply(content=content, mention_author=False)

bot = GoidaBot()

@bot.tree.context_menu(name="Перевести с Кристалийского")
async def translate_from_crystalian(
    ctx: Interaction,
    message: Message
) -> None:
    qwerty = (
        "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
    )
    russian = (
        "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"
    )
    table = str.maketrans(qwerty, russian)
    result = message.content.translate(table)
    await reply(ctx, result)

@bot.tree.context_menu(name="Translate into English")
async def translate_into_english(ctx: Interaction, message: Message) -> None:
    await ctx.response.defer(ephemeral=True)
    result = await translate(message.content, "en")
    await reply(ctx, result, True)

@bot.tree.context_menu(name="Перевести на русский")
async def translate_into_russian(ctx: Interaction, message: Message) -> None:
    await ctx.response.defer(ephemeral=True)
    result = await translate(message.content, "ru")
    await reply(ctx, result, True)

@bot.tree.context_menu(name="Посчитать")
async def context_calculator(ctx: Interaction, message: Message) -> None:
    await ctx.response.defer(ephemeral=True)
    result = calculate(message.content)
    await reply(ctx, result, True)

@bot.tree.command(description="Скока времени сливать банки")
@app_commands.choices(
    energy_multiplier = [
        app_commands.Choice(name="1x", value=1),
        app_commands.Choice(name="2x", value=2),
        app_commands.Choice(name="3x", value=3),
        app_commands.Choice(name="4x", value=4),
        app_commands.Choice(name="5x", value=5),
        app_commands.Choice(name="6x", value=6),
        app_commands.Choice(name="7x", value=7),
        app_commands.Choice(name="8x", value=8),
        app_commands.Choice(name="9x", value=9),
        app_commands.Choice(name="10x", value=10)
    ],
    song_duration=[
        app_commands.Choice(name="Envy", value=74),
        app_commands.Choice(name="Sage", value=150),
        app_commands.Choice(name="LNF", value=156),
        app_commands.Choice(name="Fire dance", value=91)
    ]
)
@app_commands.describe(
    energy_count="Скока банок надо слить",
    energy_multiplier="Множитель банок",
    song_duration="Какую песенку сосем",
    gph="Игр в час"
)
async def energy(
    ctx: Interaction,
    energy_count: int,
    energy_multiplier: int,
    song_duration: int = 0,
    gph: int = 0
) -> None:
    games_count = energy_count // energy_multiplier
    if song_duration: 
        total_seconds = song_duration*(games_count + 1)
    elif gph:
        total_seconds = 3600//gph * games_count
    if total_seconds:
        total_minutes = total_seconds // 60
        minutes = total_minutes % 60
        hours = total_minutes // 60
        result = f"{total_minutes} минут | {hours} часов, {minutes} минут"
    else:
        result = "Выбери либо песенку либо гпх"
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
    member="Чел"
)
async def member_id(ctx: Interaction, member: Member) -> None:
    result = member.id
    await reply(ctx, result)

@bot.tree.command(description="Найти ориг ник чела")
@app_commands.describe(
    member="Чел"
)
async def member_name(ctx: Interaction, member: Member) -> None:
    name = member.global_name
    result = name if name else member.name
    await reply(ctx, result)

@bot.tree.command(description="Найти аву чела")
@app_commands.describe(
    member="Чел"
)
async def member_avatar(ctx: Interaction, member: Member) -> None:
    result = member.display_avatar
    await reply(ctx, result)

@bot.tree.command(description="Посчитать длину строки")
@app_commands.describe(text="Пиши свою строку")
async def length(ctx: Interaction, text: str) -> None:
    result = len(text)
    await reply(ctx, result)

@bot.tree.command(description="Калькулятор")
@app_commands.describe(expression="Напиши выражение, типа 2+2")
async def calculator(ctx: Interaction, expression: str) -> None:
    result = calculate(expression)
    await reply(ctx, result)

@bot.tree.command(description="Скока времени ишачит бот")
async def uptime(ctx: Interaction) -> None:
    duration = datetime.now() - bot.start_time
    total_minutes = duration.seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    result = f"{hours} часов {minutes} минут"
    await reply(ctx, result)

@bot.tree.command(description="Проверить синхронизацию")
async def check_sync(ctx: Interaction) -> None:
    result = bot.sync_enabled
    await reply(ctx, result)

async def translate(source_text: str, target_language: str) -> str:
    translator = Translator()
    try:
        translation = await translator.translate(
            source_text[:bot.max_message_len],
            targetlang=target_language)
        result = translation.text
    except TranslationError:
        result = "*Translation error, try again*"
    return result

async def reply(
    ctx: Interaction,
    result: str | int | float | bool,
    defer: bool = False,
    silent: bool = False
) -> None:
    """Send the result."""
    if result == "":
        result = "Полундра штото пошло нетак"
    if defer:
        await ctx.followup.send(result, silent=silent)
    else:
        await ctx.response.send_message(result, silent=silent)

def calculate(expression: str) -> str:
    if len(expression) <= 32:
        try:
            simpleeval.MAX_POWER = 8
            result = simpleeval.simple_eval(expression.replace(",", ""))
        except Exception:
            result = "По понятиям пиши, вотак вот: 1*4/8-8"
    else:
        result = "Длинное выражение"
    return result

def is_human_in_text_channel(
    author: Member,
    channel: Messageable
) -> bool:
    result = not author.bot and type(channel) is TextChannel
    return result

def get_room_prefix(channel_name: str) -> str:
    if len(channel_name) != bot.channel_name_len:
        return ""
    if channel_name[0] != bot.room_letter:
        return ""
    if channel_name[2] != "-":
        return ""
    room_number = channel_name[1]
    if not room_number.isdecimal():
        return ""
    room_prefix = f"{bot.room_letter}{room_number}-"
    return room_prefix

def is_sekai_code(text: str) -> bool:
    result = len(text) == bot.sekai_code_len and text.isdecimal()
    return result

def is_manager(author: Member) -> bool:
    result = any(role.name in bot.manager_roles for role in author.roles)
    return result

def main() -> None:
    install()
    token = environ["BOT_TOKEN"]
    bot.run(token)

if __name__ == "__main__":
    main()
