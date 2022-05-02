import dataclasses
from aiogram.types.input_media import MediaGroup
from typing import Tuple, List, Optional, Dict

@dataclasses.dataclass
class VkLink:
    """
    External link from vk with preview
    """
    url: str = None
    title: str = None
    photo: str = None


@dataclasses.dataclass
class VkVideo:
    """
    VK video instance with url and title
    """
    url: str = None
    title: str = None


@dataclasses.dataclass
class VkPost:
    """
    VK post instance 
    """
    id: int = None
    from_id: Optional[int] = None
    owner_id: Optional[int] = None
    date: Optional[int] = None
    text: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[VkVideo]] = None
    external_link: Optional[VkLink] = None
    is_pinned: bool = False


@dataclasses.dataclass
class VkGroup:
    """
    Information about vk group 
    """
    group_name: str = None
    id: int = None
    is_closed: bool = False
    domain: str = None
    photo: Optional[str] = None

@dataclasses.dataclass
class DataBaseGroup:
    """
    Information about group from database with members ids
    """
    domain: str
    id: int
    group_name: str
    post_date: int
    members: List[int]

@dataclasses.dataclass
class DataBaseUserGroup:
    domain: str
    last_update_date: int

@dataclasses.dataclass
class DataBaseUser:
    """
    Information about user from database
    """
    user_id: int
    groups : Optional[List[DataBaseUserGroup]]

@dataclasses.dataclass
class TelegramPost:
    """
    Information about vk group 
    """
    date: int = None
    group_name: int = None
    texts: List[str] = None
    media: MediaGroup = None