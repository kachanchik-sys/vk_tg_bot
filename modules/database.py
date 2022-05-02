from typing import List

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import logging

from data_classes import DataBaseGroup, DataBaseUser, DataBaseUserGroup


Base = declarative_base()


class DataBaseGroupError(Exception):
    def __init__(self, group_name: str, message: str = None) -> None:
        self.group_name = group_name
        self.message = message

    def __str__(self) -> str:
        if self.message is None:
            return f'Group "{self.group_name}" is not exists in Database'
        else:
            return self.message


class DataBaseUserError(Exception):
    def __init__(self, user_id: int, message: str = None) -> None:
        self.user_id = user_id
        self.message = message

    def __str__(self) -> str:
        if self.message is None:
            return f'User "{self.user_id}" is not exists in Database'
        else:
            return self.message


class DataBaseTypeError(Exception):
    def __init__(self, element, type, message: str = None) -> None:
        self.element = element
        self.type = type
        self.message = message

    def __str__(self) -> str:
        if self.message is None:
            return f'User_id must be "{self.type}" not a "{type(self.element)}"'
        else:
            return self.message


class DataBaseUsersGroupError(Exception):
    pass


class UsersGroup(Base):
    __tablename__ = 'Users_group'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('Users.user_id'))
    domain = Column(Integer, ForeignKey('Groups.domain'))
    last_update_date = Column(Integer, nullable=False)


class Groups(Base):
    __tablename__ = 'Groups'
    group_id = Column(Integer, primary_key=True)
    domain = Column(String, nullable=False)
    name = Column(String, nullable=False)
    date_of_last_post = Column(Integer, nullable=False)


class Users(Base):
    __tablename__ = 'Users'
    user_id = Column(Integer, primary_key=True)


class Database:
    """
    Сlass for working with the bot's database
    """

    def __init__(self, path_to_database: str) -> None:
        """Constructor"""
        engine = create_engine(path_to_database)
        Base.metadata.create_all(engine)
        self.sql_session = Session(engine)

        self.groups = Groups
        self.users = Users
        self.users_group = UsersGroup
        log.info("DataBase initialized")

    def is_group_has_member(self, domain: str, user_id: int) -> bool:
        if not self.is_group_exists(domain) or not self.is_user_exists(user_id):
            return False
        return user_id in self.get_group(domain).members

    def is_user_exists(self, user_id: int) -> bool:
        return not self.sql_session.query(Users.user_id).filter(Users.user_id == user_id).first() is None

    def is_group_exists(self, domain: str) -> bool:
        return not self.sql_session.query(Groups.domain).filter(Groups.domain == domain).first() is None

    def create_group(self, domain: str, group_id: int, group_name: str):
        """Create new group in database

        Args:
            domain (str): group short name
            group_id (int): group id
        """
        if self.is_group_exists(domain):
            raise DataBaseGroupError(domain, f'Group "{domain}" alredy exists')
        self.sql_session.add(
            Groups(domain=domain, group_id=group_id, date_of_last_post=0, name=group_name))
        self.sql_session.commit()

    def create_user(self, user_id: int):
        """Create new user in database

        Args:
            user_id (int): telegram id of user

        Raises:
            DataBaseUserError: called if user alredy exists in database
        """
        if not isinstance(user_id, int):
            raise DataBaseTypeError(user_id, int)

        if self.is_user_exists(user_id):
            raise DataBaseUserError(user_id, f'User "{user_id}" alredy exists')
        self.sql_session.add(Users(user_id=user_id))
        self.sql_session.commit()

    def add_member_to_group(self, domain: str, user_id: int):
        """
        Add new member to existing group

        Args:
            domain (str): group's short name
            user_id (int): member's id

        Raises:
            DataBaseUsersGroupError: Called if member exist in database
        """
        if not isinstance(domain, str):
            raise DataBaseTypeError(domain, str)
        if not isinstance(user_id, int):
            raise DataBaseTypeError(user_id, int)
        if not self.is_group_exists(domain):
            raise DataBaseGroupError(domain)
        if not self.is_user_exists(user_id):
            raise DataBaseUserError(user_id)

        if self.is_group_has_member(domain, user_id):
            raise DataBaseUsersGroupError(
                f'The user "{user_id}" is already a member of this group "{domain}"')
        self.sql_session.add(UsersGroup(domain=domain, user_id=user_id, last_update_date=0))
        self.sql_session.commit()

    def del_member_of_group(self, domain: str, user_id: int):
        """
        Delete member from group's subscribers

        Args:
            domain (str): short group's name
            user_id (int): user's id

        Raises:
            DataBaseUsersGroupError: Called if user is not a subscriber of group
        """
        if not isinstance(domain, str):
            raise DataBaseTypeError(domain, str)
        if not isinstance(user_id, int):
            raise DataBaseTypeError(user_id, int)
        if not self.is_group_exists(domain):
            raise DataBaseGroupError(domain)
        if not self.is_user_exists(user_id):
            raise DataBaseUserError(user_id)

        if not self.is_group_has_member(domain, user_id):
            raise DataBaseUsersGroupError(
                f'The user "{user_id}" is not a member of this group "{domain}"')
        self.sql_session.query(UsersGroup)\
            .filter(UsersGroup.domain == domain).filter(UsersGroup.user_id == user_id).delete(False)
        self.sql_session.commit()

    def get_user(self, user_id: int) -> DataBaseUser:
        """get information about user subscribes

        Args:
            user_id (int): telegram user id

        Raises:
    
            DataBaseUserError: called if the user is don't exists in the bot database 

        Returns:
            DataBaseUser: user object with arguments "user_id" and "groups"
        """
        if not self.is_user_exists(user_id):
            raise DataBaseUserError(user_id)
        user_groups = list(map(
            lambda raw_group: DataBaseUserGroup(raw_group.domain, raw_group.last_update_date),
            self.sql_session.query(UsersGroup).filter(
                UsersGroup.user_id == user_id).all()
        ))
        return DataBaseUser(user_id, user_groups)

    def get_group(self, domain: str) -> DataBaseGroup:
        """
        Return information about group like a domain, group id, linux time of last post and members ids

        Args:
            domain (str): short group's name

        Raises:
            DataBaseGroupError: Called if group is not exist in bot's database

        Returns:
            DataBaseGroup: group instance
        """
        if not isinstance(domain, str):
            raise DataBaseTypeError(domain, str)
        if not self.is_group_exists(domain):
            raise DataBaseGroupError(domain)
        group = self.sql_session.query(Groups).filter(
            Groups.domain == domain).first()
        members = list(map(
            lambda raw_user_id: raw_user_id.user_id,
            self.sql_session.query(UsersGroup).filter(
                UsersGroup.domain == domain).all()
        ))
        return DataBaseGroup(domain, group.group_id, group.name, group.date_of_last_post, members)

    def get_all_groups(self) -> List[DataBaseGroup]:
        """
        Return all existed in bot's database groups with information 

        Returns:
            List[DataBaseGroup]: list of groups instances

        Yields:
            Iterator[List[DataBaseGroup]]: list of groups instances
        """
        groups = list(map(
            # Extracts the group name from the tuple like ('name',)
            lambda raw_group_name: raw_group_name.domain,
            self.sql_session.query(Groups).all()
        ))
        for group in groups:
            yield self.get_group(group)

    def get_all_users(self) -> List[DataBaseUser]:
        """
        Return all existed in bot's database groups with information 

        Returns:
            List[DataBaseGroup]: list of groups instances

        Yields:
            Iterator[List[DataBaseGroup]]: list of groups instances
        """
        users_ids = list(map(
            # Extracts the group name from the tuple like ('name',)
            lambda user: user.user_id,
            self.sql_session.query(Users).all()
        ))
        for user_id in users_ids:
            yield self.get_user(user_id)

    def update_group_info(self, domain: str, new_post_date: str, new_group_name: str):
        """
        Updates last group post time

        Args:
            domain (str): group's short name
            new_post_date (str): [description]

        Raises:
            DataBaseGroupError: Called if group is not exists
        """
        if not self.is_group_exists(domain):
            raise DataBaseGroupError(domain)

        group: Groups = self.sql_session.query(Groups).filter(
            Groups.domain == domain).first()
        if not new_post_date == group.date_of_last_post:
            group.date_of_last_post = new_post_date
            self.sql_session.commit()
        if not new_group_name == group.name:
            group.name = new_group_name
            self.sql_session.commit()

    def update_user_group_date(self, user_id: int, domain: str, new_date: int) -> None:
        """
        Updates the date of the last group post received by the user 

        Args:
            user_id (int): Telegram id of user
            domain (str): Domain of vk group
            new_date (int): date received by the user

        Raises:
            DataBaseGroupError: Group does not exists in database
            DataBaseUserError: User does not exists in database
            DataBaseUsersGroup: User is not subscribed to a group
        """
        if not self.is_group_exists(domain):
            raise DataBaseGroupError(domain)
        if not self.is_user_exists(user_id):
            raise DataBaseUserError(user_id)
        if not self.is_group_has_member(domain, user_id):
            raise DataBaseUsersGroupError(f"Group {domain} has not user with id {user_id}")
        user_group: UsersGroup = self.sql_session.query(UsersGroup).filter(UsersGroup.domain == domain).filter(UsersGroup.user_id == user_id).first()
        if user_group.last_update_date < new_date:
            user_group.last_update_date = new_date
            self.sql_session.commit()



    def del_user(self, user_id: int) -> None:
        """
        Delete user from database

        Args:
            user_id (int): current id of user
        """
        if not self.is_user_exists(user_id):
            raise DataBaseUserError(user_id, f'User "{user_id}" does not exists')
        user_info = self.get_user(user_id)
        for group_domain in user_info.groups:
            self.del_member_of_group(group_domain, user_id)
        self.sql_session.query(Users)\
            .filter(Users.user_id == user_id).delete(False)
        self.sql_session.commit()
        
    def del_group(self, domain: str) -> None:
        """
        Delete group from database

        Args:
            user_id (int): current id of user
        """
        if not self.is_group_exists(domain):
            raise DataBaseGroupError(domain, f'Group "{domain}" does not exists')
        if self.sql_session.query(UsersGroup).filter(UsersGroup.domain == domain).all():
            raise DataBaseGroupError(domain, "Group has members and can not deleted")
        self.sql_session.query(Groups).filter(Groups.domain == domain).delete(False)
        self.sql_session.commit()

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [%(levelname)s] (file: %(module)s) (func: %(funcName)s) (line: %(lineno)d) ==> %(message)s",
        datefmt='%H:%M:%S',
    )
    log = logging.getLogger()
    db = Database('sqlite:///databases/tet.db')
    user_id = 1234
    domain = "baobab"
    if not db.is_group_exists(domain):
        db.create_group(domain, 2, domain)
    if not db.is_user_exists(user_id):
        db.create_user(user_id)
    if not db.is_group_has_member(domain, user_id):
        db.add_member_to_group(domain, user_id)
    print(db.get_user(user_id))
    db.update_user_group_date(user_id, domain, 123456789)

    


else:
    log = logging.getLogger()
