import time
import logging
from typing import Tuple, List, Optional, Dict, Union
from vk_api import vk_api
from data_classes import VkGroup, VkLink, VkPost, VkVideo
import requests

class VkGroupInfoError(Exception):
    def __init__(self, message: str = None) -> None:
        self.message = message

    def __str__(self) -> str:
        if self.message is None:
            return "Can't get information about group"
        else:
            return self.message


class VkGroupPostError(Exception):
    def __init__(self, message: str = None) -> None:
        self.message = message

    def __str__(self) -> str:
        if self.message is None:
            return "Can't get group post"
        else:
            return self.message


class ApiParser:
    """
    Api parser for work with VK
    """

    def __init__(self, token: str) -> None:
        """
        Constructor
        """
        vk_session = vk_api.VkApi(token=token)
        self.__api = vk_session.get_api()

    def get_last_group_post(self, group_id: int) -> VkPost:
        """Get lastest post from vk group

        Args:
            group_id (int): current group id

        Returns:
            VkPost: VK group post instance
        """
        group_posts = self.get_group_posts(group_id)
        if len(group_posts) == 1:   # If group have only 1 post
            return group_posts[0]
        elif group_posts[0].id > group_posts[1].id:
            return group_posts[0]
        else:
            return group_posts[1]

    def get_group_posts(self, group_id: int, posts_count: int = 3) -> Tuple[VkPost,]:
        """Receives posts from groups that do not contain advertising.
        May return fewer posts than specified in posts_count

        Args:
            group_id (int): current group id
            posts_count (int, optional): max count of parsed posts. Defaults to 3.

        Returns:
            Tuple[VkPost]: tuple of VK post instances
        """
        for i in range(10):
            try:
                # Gather posts via VkApi
                response: dict = self.__api.wall.get(
                    owner_id=f'-{group_id}', count=posts_count)
                # with open('response.json', 'w') as f:
                #     json.dump(response, f)
                break
            except requests.ConnectionError:
                logging.error('Connection error, wait a minute')
                time.sleep(60)

        # Filter out ads
        received_raw_posts: List[Dict] = response.get('items')
        raw_posts_without_ads: List[Dict] = list(filter(
            lambda post: not post.get('marked_as_ads'),
            received_raw_posts
        ))
        # Pack data into VkPost objects
        posts: Tuple[VkPost] = tuple(map(
            self.__get_post_data,
            raw_posts_without_ads
        ))

        return posts

    def get_group_info(self, group_uniq: Union[int, str]) -> VkGroup:
        """Get information about group

        Args:
            group_uniq (str): group short name

        Raises:
            VkGroupInfoError: called when group not exists

        Returns:
            VkGroup: VK group information instance
        """
        try:
            response: dict = self.__api.groups.getById(group_id=group_uniq)[0]
            return VkGroup(
                id=response.get('id'),
                group_name=response.get('name'),
                is_closed=response.get('is_closed') != 0,
                domain=response.get('screen_name'),
                photo=response.get('photo_200')
            )
        except Exception as exception:
            if '[100]' in str(exception):
                raise VkGroupInfoError(
                    f'Group with domain "{group_uniq}" does not exists').with_traceback(None)
            raise exception.with_traceback(None)

    def __get_post_data(self, raw_post: Dict) -> VkPost:
        """
        Obtain data from the post
        :param raw_post: raw post as dictionary
        :return: parsed vk post as VkPost instance
        """
        # Parse data
        id: int = raw_post.get('id')
        from_id: int = raw_post.get('from_id')
        owner_id: int = raw_post.get('owner_id')
        date: int = raw_post.get('date')
        text: str = raw_post.get('text')
        is_pinned: bool = not raw_post.get('is_pinned') is None
        photos: Optional[List[str]] = self.__parse_photo_links(raw_post)
        videos: Optional[List[VkVideo]] = self.__parse_videos(raw_post)
        external_link: Optional[List[str]] = self.__parse_external_link(raw_post)

        # Pack data
        parsed_post: VkPost = VkPost(
            id=id,
            from_id=from_id,
            owner_id=owner_id,
            date=date,
            text=text,
            photos=photos,
            videos=videos,
            external_link=external_link,
            is_pinned=is_pinned
        )
        return parsed_post

    @staticmethod
    def __parse_photo_links(raw_post: Dict) -> Optional[List[str]]:
        """
        Parse raw post and return photos urls

        Args:
            raw_post (Dict): raw post from vk

        Returns:
            Optional[List[str]]: list of photos urls
        """
        photo_attachments = filter(
            lambda item: item.get('type') == 'photo',
            raw_post.get('attachments', tuple((dict(), )))
        )
        photos: List[str] = []
        for attachment in photo_attachments:
            photos.append(attachment['photo']['sizes'][-1]['url'])

        return photos

    @staticmethod
    def __parse_videos(raw_post: Dict) -> Optional[List[VkVideo]]:
        """
        Parse raw post and return list of vk video instances with video url and title

        Args:
            raw_post (Dict): raw post from vk

        Returns:
            Optional[List[VkVideo]]: list if vk video instances
        """
        video_attachments = filter(
            lambda item: item.get('type') == 'video',
            raw_post.get('attachments', tuple((dict(), )))
        )
        videos: List[VkVideo] = []
        for attachment in video_attachments:
            owner_id = attachment['video']['owner_id']
            group_id = attachment['video']['id']
            videos.append(
                VkVideo(
                    url=f'https://vk.com/video{owner_id}_{group_id}',
                    title=attachment['video']['title']
                )
            )
        return videos

    @staticmethod
    def __parse_external_link(raw_post: Dict) -> Optional[VkLink]:
        """
        Parse raw post and return vk link instance with url to external resorce and title

        Args:
            raw_post (Dict): raw post from vk

        Returns:
            Optional[VkLink]: vk link instance
        """
        link_attachments = filter(
            lambda item: item.get('type') == 'link',
            raw_post.get('attachments', tuple((dict(),)))
        )
        external_link: VkLink = None
        for attachment in link_attachments:
            link: Dict = attachment['link']
            if link.get('photo') != None:
                photo = link['photo']['sizes'][-1]['url']
            else:
                photo = None
            external_link = VkLink(
                url=link['url'],
                title=link['title'],
                photo=photo
            )
        return external_link


if __name__ == "__main__":
    pass
