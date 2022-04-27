#!/bin/bash

# Variables
vnev_name="vnev"

# Launches the bot if it is installed
if [ -e requirements.txt ] && [ -d $vnev_name ]; then
    echo "Launch bot"
    $vnev_name/bin/python3 main.py 
    exit
fi

# Install bot
echo "Start installing"

# Checks if the required programs are installed
echo "Check python"
if [ -z `which python3` ]; then
    echo "Python 3 is not found, try installing it with 'apt install python3'"
    exit
fi
echo "Check pip"
if [ -z `which pip` ]; then
    echo "Pip is not found, try installing it with 'apt install python3-pip'"
    exit
fi
echo "Check virtualenv"
if [ -z `which virtualenv` ]; then
    echo "Virtualenv is not found, try installing it with 'apt install virtualenv'"
    exit
fi

# Creates a virtual environment for the project to avoid library conflicts
echo "Create virtual environment"
virtualenv $vnev_name -q
echo "Done"

# Installs dependencies for the project
echo "Install requirements"
if [ -e requirements.txt ]; then
    $vnev_name/bin/pip3 install -q -r "requirements.txt"
else
    echo "Can't find the requirements.txt, try downloading the project again"
    exit
fi

# Get input from user
echo "Please enter VK token, if you don't have it and you don't know how to get it please read README in FAQ"
read vk_token
echo "OK. Now enter Telegram bot token. Also see FAQ if you don't have it"
read tg_bot_token
echo "And lastly, add the id of the administrator who will have access to the control panel of the bot"
read admin_id

# Create settings.ini file
echo "[Bot]
update_timer = 600
telegram_token = $tg_bot_token
vk_token = $vk_token
database_path = sqlite:///databases/release.db
admin_id = $admin_id
" >> settings.ini

# Offer to run a bot
echo "Installation complete, start the bot? [Y/N]"
read ans
if [ $ans == "Y" ] || [ $ans == "y" ]; then
    $vnev_name/bin/python3 main.py 
fi