#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""A discord bot."""

from asyncio import wait_for, TimeoutError
from re import compile
from os import environ
from gpytranslate import Translator, TranslationError
from simpleeval import simple_eval
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

class GoidaBot(Client):
    user: ClientUser
    def __init__(self) -> None:
        intents = Intents.default()
        intents.message_content = True
        activity = Game(name="Форсакен")
        super().__init__(
            intents=intents,
            help_command=None,
            activity=activity,
            chunk_guilds_at_startup=False)
        self.tree = app_commands.CommandTree(self)
        self.max_message_len = 2000
        self.channel_name_regex = compile(r"^(g\d-)(\d{5}|xxxxx)(-[1-5])?$")
        self.sekai_code_regex = compile(r"^(\d{5}|xxxxx)$")
        self.manager_roles = {
            1470549658454458471,  # Раннер ростера
            1316002183895973979,  # Менеджер
            1316002661895508058  # Интерн
        }

    async def setup_hook(self) -> None:
        if environ["SYNC_BOT"] == "1":
            await self.tree.sync()

    async def on_message(self, message: Message) -> None:
        author = message.author
        message_text = message.content
        channel = message.channel
        channel_name = channel.name
        if not (
            type(channel) is TextChannel
            and author.id != self.user.id
            and self.sekai_code_regex.match(message_text)
            and (channel_match := self.channel_name_regex.match(channel_name))
            and any(role.id in self.manager_roles for role in author.roles)
        ):
            return
        prefix = channel_match.group(1)
        name = prefix + message_text
        try:
            content = f"~~{channel_name}~~ ➔ **`{name}`**"
            reason = "старый код румы был депнут в казик"
            await wait_for(channel.edit(name=name, reason=reason), timeout=2)
        except TimeoutError:
            content = f"Новый код румы: **`{name}`**\n> Юзни `%rm code`"
        except Forbidden:
            content = "**У меня нет прав** на управление каналами"
        await message.reply(content=content, mention_author=False)

bot = GoidaBot()

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
    result = await calculate(message.content)
    await reply(ctx, result, True)

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

@bot.tree.command(description="Калькулятор")
@app_commands.describe(expression="Напиши выражение, типа 2+2")
async def calculator(ctx: Interaction, expression: str) -> None:
    result = await calculate(expression)
    await reply(ctx, result)

@bot.tree.command(description="Посчитать длину строки")
@app_commands.describe(text="Пиши свою строку")
async def length(ctx: Interaction, text: str) -> None:
    result = len(text)
    await reply(ctx, result)

@bot.tree.command(description="Проверить жив ли бот")
async def check_bot(ctx: Interaction) -> None:
    result = "Гойда"
    await reply(ctx, result)

async def calculate(expression: str) -> str:
    try:
        result = simple_eval(expression.replace(",", ""))
    except Exception:
        result = "По понятиям пиши, вотак вот: 1*4/8**8 + (5-2)"
    return result

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
    result: str | int | float,
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

if __name__ == "__main__":
    bot.run(environ["BOT_TOKEN"])
