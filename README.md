# VK to Telegram Bot
Sends posts from the walls of vk groups to telegram

## Requirements
- telegram bot api token
- vk api token
- Bot's admin telegram id for Start-up notification

## Installation
### For Linux with apt
1. Run `launch.sh` for linux
2. Enjoy
### Manual
1. Create vitual environment by `vitualenv vnev` 
2. To activate the virtual environment run `source vnev/bin/activate` on linux or `vnev/Scripts/activate.ps1` on windows
3. Install requirements. Use command `pip install -r requirements.txt`
4. Change `settings_sample.ini` and rename to `settings.ini`
5. Run bot `python3 main.py`



## How to use
1. Run bot and send command `/start` in telegram
2. After ansver send domain or link to group (as example `https://vk.com/vk` or `vk`) also you can send link to post from group wall (example `https://vk.com/vk?w=wall-22822305_1293458`)
3. Done

## For bot admin
The bot's administrator (the person whose ID is specified in the settings) can...
- Make a mass mailing to all bot users with the `/spam` command\
That's all for now, the rest of the features will appear later

## FAQ
- Q: Where i can get telegram bot api token?\
A: You must create a bot using @BotFather on telegram.
- Q: Okay, then where do I get the vk api token?\
A: Go to https://vkhost.github.io, select vk.com and follow the instructions.
- Q: How will the bot know when there are new posts on vk?\
A: Bot parses each group in the database every 10 minutes.
- Q: Is it possible to change this delay?\
A: Yes! You can change this parameter in settings. Set the `update_timer` variable to a value in seconds .
- Q: Where can I see an example of how the bot actually works?\
A: https://t.me/VKpost_to_tg_bot

## TODO
- [ ] CMD script for auto install on windows
- [x] Personal time in GroupUser
- [x] Manual parse vk by user
- [ ] Parse music, files and videos
- [ ] Admin panel 
  - [ ] Kill and reboot bot
  - [ ] Get logs
  - [ ] Get database

## Known issues
- Bot stops parsing vk and says there are no updates, although this is not true
- Sends posts with only a group header if it does not find text or photos
- Sends the same post twice to a user when adding a new group. This will be resolved when I add a personal time to GroupUser

## Contacts
Telegram - https://t.me/mashkachan
