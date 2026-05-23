import asyncio
import logging
import os

from vkwave.bots import SimpleLongPollBot

from vk_bot.handlers.router import register_handlers


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [VK] %(levelname)s %(message)s",
    )

    bot = SimpleLongPollBot(
        tokens=os.environ["VK_BOT_TOKEN"],
        group_id=int(os.environ["VK_GROUP_ID"]),
    )

    register_handlers(bot)

    logging.info("VK bot started")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
