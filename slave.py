#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""A discord bot."""

from asyncio import wait_for
from os import environ
from uvloop import install
from discord import (
    Intents,
    Client,
    Game,
    Interaction,
    ClientUser,
    Message,
    Member,
    Forbidden
)

class SlaveBot(Client):
    user: ClientUser
    def __init__(self) -> None:
        activity = Game("я робот долбаеб")
        intents = Intents.default()
        intents.message_content = True
        super().__init__(
            intents=intents,
            activity=activity,
            chunk_guilds_at_startup=False)
        self.master_id = int(environ["MASTER_ID"])
        self.sekai_code_len = 5

    async def on_message(self, message: Message) -> None:
        """Backup sekai room code highlighting."""
        if not is_master(message.author):
            return
        message_text = message.content
        if message_text[0] != "!":
            return
        name = message_text.split()[1]
        channel = message.channel
        channel_name = channel.name
        if name == channel_name:
            return
        old_code = channel_name[-self.sekai_code_len:]
        new_code = name[-self.sekai_code_len:]
        content = f"~~{old_code}~~ → **`{new_code}`**"
        try:
            reason = "ебучие рерумы"
            await wait_for(channel.edit(name=name, reason=reason), timeout=2.0)
        except TimeoutError:
            content = f"# Юзни `%rm {new_code}` :warning:"
        except Forbidden:
            content = "**У меня нет прав** на управление каналами"
        await message.reply(content=content, mention_author=False)

bot = SlaveBot()

def is_master(author: Member) -> bool:
    result = author.bot and author.id == bot.master_id
    return result

def main() -> None:
    install()
    token = environ["SLAVE_TOKEN"]
    bot.run(token)

if __name__ == "__main__":
    main()
