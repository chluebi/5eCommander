import logging
import sys

def setup_logging() -> logging.Logger:
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")

    file_handler = logging.FileHandler(
        filename="./botlogs/bot.log", encoding="utf-8", mode="a"
    )

    file_handler.setFormatter(formatter)

    logger = logging.getLogger("discord")
    logger.handlers.clear()

    logger.addHandler(file_handler)

    return logger


logger = setup_logging()