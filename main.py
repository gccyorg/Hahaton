"""Start the bot: python main.py"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from cars import load_cars
from config import load_config
from handlers import router


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    logging.info("Loading records from %s", config.data_path)
    # Read the JSON once. Later messages only look up the dictionaries inside cars.
    cars = load_cars(config.data_path)
    logging.info("Indexed %s records", cars.total)

    bot = Bot(
        token=config.bot_token,
        # Cards use <b> labels. Values from the dataset are escaped before sending.
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    # Any handler with an argument named cars receives this object.
    await dispatcher.start_polling(bot, cars=cars)


if __name__ == "__main__":
    asyncio.run(main())
