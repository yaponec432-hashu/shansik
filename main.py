#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""A discord bot."""

from asyncio import wait_for
from os import environ
from gpytranslate import Translator, TranslationError
from discord.abc import Messageable
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
        self.channel_name_len = 8
        self.sekai_code_len = 5
        self.manager_roles = {"Раннер ростера", "Менеджер", "Интерн"}

    async def setup_hook(self) -> None:
        if environ["BOT_SYNC_ENABLED"] == "1":
            await self.tree.sync()

    async def on_message(self, message: Message) -> None:
        message_text = message.content
        author = message.author
        channel = message.channel
        channel_name = channel.name
        if not (
            is_human_in_text_channel(author, channel)
            and is_sekai_code(message_text)
            and (prefix := get_room_prefix(channel_name))
            and is_manager(author)
        ):
            return
        name = prefix + message_text
        content = f"~~{channel_name}~~ ➔ **`{name}`**"
        try:
            reason = "старый код румы был депнут в казик"
            await wait_for(channel.edit(name=name, reason=reason), timeout=2.0)
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

@bot.tree.command(description="Проверить жив ли бот")
async def check_bot(ctx: Interaction) -> None:
    result = "Гойда"
    await reply(ctx, result)

def is_human_in_text_channel(
    author: Member,
    channel: Messageable
) -> bool:
    result = not author.bot and type(channel) is TextChannel
    return result

def get_room_prefix(channel_name: str) -> str:
    room_letter = "g"
    prefix = ""
    if (
        len(channel_name) == bot.channel_name_len
        and channel_name.startswith(room_letter)
        and channel_name[1].isdigit()
        and channel_name[2] == "-"
    ):
        prefix += f"{room_letter}{room_number}-"
    return prefix

def is_sekai_code(text: str) -> bool:
    result = len(text) == bot.sekai_code_len and text.isdigit()
    return result

def is_manager(author: Member) -> bool:
    result = any(role.name in bot.manager_roles for role in author.roles)
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
    result: str | int,
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
