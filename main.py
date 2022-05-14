from telegram_bot.bot import TelegramBot
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] (file: %(module)s) (func: %(funcName)s) (line: %(lineno)d) ==> %(message)s",
    datefmt='%H:%M:%S',
)
 
if __name__ == "__main__":
    ini_file_path = "settings_dev.ini"
    TelegramBot.run(ini_file_path)
