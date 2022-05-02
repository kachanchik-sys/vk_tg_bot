import asyncio
import configparser
import logging
import re
import urllib.parse
from typing import List, Optional, Tuple
from datetime import datetime
import time

import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, Chat, User
from aiogram.types.input_media import MediaGroup

from modules import database
from modules import vk_parser
from data_classes import DataBaseGroup, DataBaseUser, TelegramPost, VkGroup, VkPost, DataBaseUserGroup
from tools import split_text


class States(StatesGroup):
    """
    States of bot
    """
    add_group = State()
    del_group = State()
    mass_mail = State()


class Keyboard:
    """
    Bot's keyboards
    """
    # Set keyboard for main menu
    main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    main_menu.insert(KeyboardButton('Добавить группу'))
    main_menu.insert(KeyboardButton('Удалить группу'))

    # Set keyboard for states
    cancel = ReplyKeyboardMarkup(resize_keyboard=True)
    cancel.insert(KeyboardButton('Отмена'))


class TelegramBot:
    def __init__(self, database_path: str, telegram_token: str, vk_token: str, admin_id: int) -> None:
        # Set limits for counts of chars in messages sended by telegram bot. See tools.py split_text method
        self.post_char_limit = 4000 
        self.capture_char_limit = 1000

        # Creates instances
        self.admin_id = admin_id
        self.database = database.Database(database_path)
        self.bot_api = Bot(token=telegram_token)
        self.bot_dispatcher = Dispatcher(self.bot_api, storage=MemoryStorage())
        self.vk_api_parser = vk_parser.ApiParser(vk_token)

        # Registers bot event handlers
        self._reg_main_menu_handlers()
        self._reg_states_handlers()


    def _reg_main_menu_handlers(self) -> None:
        """
        Registrate commands and buttons handlers from bot's main menu
        """
        self.bot_dispatcher.register_message_handler(
            self.__send_help_message, commands=['help', 'start'])
        self.bot_dispatcher.register_message_handler(
            self.__on_add_group_button, regexp=r'^([Дд]обавить группу)$')
        self.bot_dispatcher.register_message_handler(
            self.__on_del_group_button, regexp=r'^([Уу]далить группу)$')
        self.bot_dispatcher.register_message_handler(
            self.__on_cancel_button, regexp=r'^([Оо]тмена)$') # Registre cancel command in main menu
        self.bot_dispatcher.register_message_handler(
            self.__on_comand_spam, 
            lambda msg: msg.from_user.id == self.admin_id, # Check on bot admin id from settings
            commands=['spam'])


    def _reg_states_handlers(self) -> None:
        """
        Registrate states handlers
        """
        self.bot_dispatcher.register_message_handler(
            self.__on_cancel_button, regexp=r'^([Оо]тмена)$', state=States.all_states) # Registre cancel command in all states
        self.bot_dispatcher.register_message_handler(
            self.__on_add_group_state, state=States.add_group)
        self.bot_dispatcher.register_message_handler(
            self.__on_del_group_state, state=States.del_group)
        self.bot_dispatcher.register_message_handler(
            self.__on_state_spam, state=States.mass_mail)


    async def __send_help_message(self, message: types.Message) -> None:
        """
        Send help message if user call commands 'start' or 'help'

        Args:
            message (types.Message): message instance from user
        """
        help_message: str = \
            f"Привет {message.from_user.first_name}!\n"\
            "Я бот для пересылки постов из групп Вконтакте. "\
            "Для начала нажмите на кнопку 'Добавить группу' "\
            "и отправте ссылку на группу, короткое имя группы в ВК или любой пост с ее стены, "\
            "и я буду прересылать вам новые посты как только они появятся!\n"\
            "P.S.\n"\
            "ссылка на группу - https://vk.com/eastwindiscoming\n"\
            "ее короткое имя - eastwindiscoming"
        await message.answer(
            help_message, 
            reply_markup=Keyboard.main_menu, 
            disable_web_page_preview=True
        )


    async def __on_add_group_button(self, message: types.Message) -> None:
        """
        Sets bot to the state of waiting for user to enter group to be added.
        Called if user press 'Добавить группу' button

        Args:
            message (types.Message): message instance from user
        """
        await message.reply("Введите ссылку на группу которую хотите добавить", 
        reply_markup=Keyboard.cancel)
        await States.add_group.set() # Set state of waiting while user enter group

    async def __on_del_group_button(self, message: types.Message) -> None:
        """
        Sets bot to the state of waiting for user to enter group to be deleted.
        Called if user press 'Удалить группу' button

        Args:
            message (types.Message): message instance from user
        """
        # Checks if the user is not in the database
        if not self.database.is_user_exists(message.from_user.id):
            await message.reply('Вы не являетесь пользователем бота, вам просто нечего удалять')
            return
        user_groups: List[str] = self.database.get_user(
            message.from_user.id).groups
        if not user_groups:
            await message.reply('Вы не подписаны ни на одну группу и вам нечего удалять')
            return

        groups_list: List[str] = list()
        for index, group_domain in enumerate(user_groups, 1): # Gen list of vk groups of user with html markup
            group = self.database.get_group(group_domain)
            groups_list.append(f"""{index}. '<a href="https://vk.com/{group.domain}">{group.group_name}</a>'""")

        msg: str = f"\n\nВведите номер группы из списка которую хотите удалить\
                    \nДиапозон ввода от 1 до {len(user_groups)}"
        await message.answer(
            '\n'.join(groups_list) + msg,
            reply_markup=Keyboard.cancel,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        await States.del_group.set()

    async def __on_cancel_button(self, message: types.Message, state: FSMContext) -> None:
        """
        Sets the keyboard of the main menu if the bot is in the zero state
        Called if user press 'Отмена' button
        """
        await state.finish()
        await message.answer('Возврат на главный экран', reply_markup=Keyboard.main_menu)

    async def __on_add_group_state(self, message: types.Message, state: FSMContext) -> None:
        """
        Check user input and add group to base

        Args:
            message (types.Message): message from user
            state (FSMContext): current state of bot
        """
        user_input: str = message.text # may be a domain, url to group or wall post
        raw_path: Optional[str] = urllib.parse.urlsplit(user_input).path.replace('/', '') # May be a group domain or raw id 
        user_id: int = message.from_user.id
        group_id: Optional[str] = None
        group_domain: Optional[str] = None
        logging.info(f"User '{user_id}' try add '{raw_path}' group")

        if not raw_path:
            # Empty group_name if user input https://vk.com
            await message.reply('Ссылка не содержит короткого имени группы или ее id\nПопробуйте снова')
            return
        try:
            if raw_path.startswith('wall-'): # link to wall post of group
                group_id = re.findall(r'-(.+)_', raw_path)[0] # parse group id
                group_info: VkGroup = self.vk_api_parser.get_group_info(group_id) # Get info about group
                group_domain = group_info.domain 
            else: # If just group domain
                group_domain = raw_path
                group_info: VkGroup = self.vk_api_parser.get_group_info(group_domain)
        except vk_parser.VkGroupInfoError:
            await message.reply('Такой группы не существует\nПопробуйте снова')
            return

        if self.database.is_group_has_member(group_domain, user_id):
            await message.reply('Вы уже подписаны на группу', reply_markup=Keyboard.main_menu)
            await state.finish()
            return

        if group_domain.isdigit():
            group_domain = group_info.domain

        if group_info.is_closed:
            await message.reply('Это приватная группа и бот не может ее обработать')
            return

        if not self.database.is_user_exists(user_id):
            self.database.create_user(user_id)

        if not self.database.is_group_exists(group_domain):
            self.database.create_group(group_domain, group_info.id, group_info.group_name)

        self.database.add_member_to_group(group_domain, user_id)
        await message.answer(
            f'Группа "{group_info.group_name}" успешно добавлена в ваши подписки\n'\
             'Для проверки вам отправляется закрепленный или в случае его отсупствия последний пост группы', 
            reply_markup=Keyboard.main_menu)
        group = self.database.get_group(group_domain)
        telegram_post = await self._get_post(group, True)
        await self._send_post(telegram_post.texts, telegram_post.media, user_id)
        self.database.update_user_group_date(user_id, group_domain, telegram_post.date)
        await state.finish()

    async def __on_del_group_state(self, message: types.Message, state: FSMContext) -> None:
        """Check user input and delete group from base

        Args:
            message (types.Message): message instance from user
            state (FSMContext): current state of bot
        """
        user_id: int = message.from_user.id
        groups: List[DataBaseUserGroup] = self.database.get_user(user_id).groups

        if not message.text.isdigit():
            await message.answer(
                'Вы должны ввести порядковый номер группы из указанного выше списка\nПопробуйте еще'
            )
            return

        group_index: int = int(message.text) - 1 
        if not group_index in range(len(groups)):
            await message.reply(f'Вы ввели число которого нет в списке\nПопробуйте еще')
            return

        logging.info(f"User '{user_id}' delete '{groups[group_index].domain}' group")
        self.database.del_member_of_group(groups[group_index].domain, user_id)
        await message.reply('Группа успешно удалена', reply_markup=Keyboard.main_menu)
        await state.finish()

    def _generate_post(self, vk_post: VkPost, full_group_name: str) -> Tuple[str, MediaGroup]:
        """
        Generate message text and media group for telegram post

        Args:
            vk_post (VkPost): instance of vk group post 
            full_group_name (str): long name of group

        Returns:
            Tuple[str, MediaGroup]: data for telegram post
        """
        media = MediaGroup()
        text_of_post: str = f'<a href="https://vk.com/wall{vk_post.owner_id}_{vk_post.id}">{full_group_name}</a>\n\n' # Link to post

        if vk_post.text:
            temp_post_text = vk_post.text
            # Parse vk hyper links markup and convert to html
            hyper_links = re.findall(r'(\[.*\|.*\])', temp_post_text) # Get hyper link from vk markup
            for link in hyper_links:
                group_domain, hyper_text = re.findall(r'\[(.*?)\|(.*)\]', link)[0] # Parse hyper link
                temp_post_text = temp_post_text.replace(   # Convert to html and replace text
                    link, 
                    f'<a href="https://vk.com/{group_domain}">{hyper_text}</a>'
                )
            text_of_post += temp_post_text + '\n'

        if vk_post.videos:
            for video in vk_post.videos:
                # Paste video like hyper link because i so lazy to get video from vk
                text_of_post += f'<a href="{video.url}">{video.title}</a>\n'

        if vk_post.photos:
            for photo in vk_post.photos:
                media.attach_photo(photo)

        if vk_post.external_link != None: # External link it is link from previev
            text_of_post += f'<a href="{vk_post.external_link.url}">{vk_post.external_link.title}</a>\n'
            if vk_post.external_link.photo:
                media.attach_photo(vk_post.external_link.photo)

        return text_of_post, media

    async def _send_post(self, post_texts: List[str], post_media: MediaGroup, user_id: int) -> None:
        """
        Send prepared post from vk to user in telegram 

        Args:
            post_texts (List[str]): splited post text
            post_media (MediaGroup): photo group for post
            user_id (int): id of user
        """
        try:
            chat = await self.bot_api.get_chat(user_id)
        except:
            logging.warning(f'Chat with user {user_id} does not exists. The user will be deleted from the database')
            self.database.del_user(user_id)
            return
        for index, post_text in enumerate(post_texts): 
            if not post_media.media or index != 0:  # Sends media only in the first iteration
                await self.bot_api.send_message(user_id,  post_text, 'HTML')

            elif len(post_media.media) == 1:
                photo = post_media.media[0].media
                await self.bot_api.send_photo(user_id, photo, post_text, 'HTML')

            else:
                post_media.media[0].caption = post_text
                post_media.media[0].parse_mode = 'HTML'
                await self.bot_api.send_media_group(user_id, post_media)

    async def posting(self) -> None:
        """
        Sends each user in the database a latest post from the VK groups to which he is subscribed
        """
        # Initializes the counter of updated groups (may differ from the total number of groups in the database)
        update_counter: int = 0
        groups: List[DataBaseGroup] = self.database.get_all_groups()
        for group in groups:
            
            # Deletes a group from the database if it has no users
            if not group.members:
                self.database.del_group(group.domain)
                continue
            
            # Get post from group and parse them
            telegram_post: TelegramPost = await self._get_post(group)
            # Skips sending a post if it has already been sent before
            if telegram_post.date <= group.post_date:
                continue
            # Update counter (needed for a pretty line in the logs)
            update_counter += 1
            
            # Send post to all member of group
            for user in group.members:
                # Compares if the user received the same post (for example, if he recently subscribed to a group and received as an example the last post from its wall)
                # If anyone is interested, yes, i love long line coments and code >:D
                user_group: DataBaseUserGroup = list(filter(lambda x: x.domain == group.domain, self.database.get_user(user).groups))[0]
                if user_group.last_update_date >= telegram_post.date:
                    continue
                try:
                    await self._send_post(telegram_post.texts, telegram_post.media, user)
                    self.database.update_user_group_date(user, group.domain, telegram_post.date)
                except aiogram.utils.exceptions.BotBlocked:
                    # Delete user if it stop and block bot in telegram
                    if self.database.is_user_exists(user):
                        logging.warning(f'Bot blocked by user {user}. The user will be deleted from the database')
                        self.database.del_user(user)

            self.database.update_group_info(group.domain, telegram_post.date, telegram_post.group_name)
        logging.info(f'Updated {update_counter} groups')

    def run(config_file_path: str):
        """
        Run telegram bot

        Args:
            config_file_path (str): path to configuration ini file
        """

        # Read config file
        logging.info('Reading configuration file')
        config = configparser.ConfigParser()
        config.read(config_file_path)
        admin_id = int(config.get('Bot', 'admin_id'))
        update_timer = int(config.get('Bot', 'update_timer'))
        telegram_token = config.get("Bot", "telegram_token")
        vk_token = config.get("Bot", "vk_token")
        database_path = config.get("Bot", "database_path")

        # Initialize bot class
        logging.info('Init bot class')
        telegram_bot = TelegramBot(database_path, telegram_token, vk_token, admin_id)
        loop = asyncio.get_event_loop()

        # Get bot name
        bot_info: User = loop.run_until_complete(asyncio.gather(
            telegram_bot.bot_api.get_me()
        ))[0]

        # Get bot admin name
        # Note: If chat does not exist there will be exception (For example if you run bot first time without chat)
        try:
            # Get info about chat of admin
            admin_chat: Chat = loop.run_until_complete(asyncio.gather(
                telegram_bot.bot_api.get_chat(admin_id)
            ))[0]
            # Get admin's username
            admin_username: str = admin_chat.username
            # Send message to admin
            logging.info(f'Try send message to bot`s admin "{admin_username}"')
            loop.run_until_complete(telegram_bot.bot_api.send_message(admin_id, 'Bot is running'))
        except:
            logging.warning("Bot can not send launch message to admin. It's normal if you launch bot first time and don't start chat with him")

        # Launch bot poling and infinit vk parser loop
        logging.info(f'Launch bot "@{bot_info.username}"')
        loop.create_task(telegram_bot.bot_dispatcher.start_polling(timeout=40, relax=0.5))
        loop.create_task(telegram_bot._launch_vk_update(update_timer))
        loop.run_forever()

    async def _launch_vk_update(self, update_timer: int):
        """
        Launch update and parse vk process

        Args:
            update_timer (int): timer to parse groups wall updates
        """
        # Start infinite updating loop
        while True:
            try:
                # Run update. Check all vk groups, parse and send to users to telegram
                logging.info("Update...")
                await self.posting()    
                # Calc time of next update
                next_update_time = datetime.fromtimestamp(time.time() + update_timer).time()
                logging.info(f"Next update in '{next_update_time.hour}:{next_update_time.minute}:{next_update_time.second}'")
                # Delay of update
                await asyncio.sleep(update_timer)
            except Exception as e:
                # I don't remember why it's needed. But I'll leave it just in case.
                logging.error(e)

    async def __on_comand_spam(self, message: types.Message):
        """
        Launch when admin type command /spam for sending message to all bot users

        Args:
            message (types.Message): message from admin with /spam command as text
        """
        await message.answer('Ожидаю текста для рассылки')
        await States.mass_mail.set()

    async def __on_state_spam(self, message: types.Message, state: FSMContext):
        """
        Sends the entered message to all bot users

        Args:
            message (types.Message): user message for spam
            state (FSMContext): bot's state
        """
        # Get list of all users in database
        users: List[DataBaseUser] = self.database.get_all_users()
        for user in users:
            try:
                # Sends a full copy of the message to the user on behalf of the bot
                await message.send_copy(user.user_id)
            except:
                logging.error(f'Cant send to {user.user_id}')
        await state.finish()

    async def _get_post(self, group: DataBaseGroup, pinned: bool = False) -> TelegramPost:
        """
        Get post from vk via vk_parser
        if pinned is true - try get last pinned wall post

        Args:
            group (DataBaseGroup): a group for which you need to get a post
            pinned (bool, optional): Is it necessary to get a fastened post. Defaults to False.

        Returns:
            TelegramPost: Prepared for sending post
        """
        vk_posts = self.vk_api_parser.get_group_posts(group.id, 4)
        vk_post: VkPost = max(vk_posts, key= lambda post: post.date)
        if pinned:
            pinned_posts = list(filter(lambda post: post.is_pinned == True, vk_posts))
            if pinned_posts:
                vk_post = pinned_posts[0]
        group_info: VkGroup = self.vk_api_parser.get_group_info(group.domain)
        full_group_name: str = group_info.group_name
        post_text, post_media = self._generate_post(vk_post, full_group_name)
        limit = self.capture_char_limit if post_media.media else self.post_char_limit # Char limits of tg bot api
        splited_post_text: List[str] = split_text(post_text, limit, self.post_char_limit)
        return TelegramPost(vk_post.id, full_group_name, splited_post_text, post_media)


if __name__ == '__main__':
        # aiogram.utils.exceptions.NetworkError:
        #   logging.warning('Bot down, wait 10 seconds')
        #   time.sleep(10)
        pass

        