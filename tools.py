from typing import List

def split_text(text: str, first_limit: int, other_limits: int) -> List[str]:
        """
        Separates text in a post to bypass telegram character limit

        Args:
            text (str): source text for separate
            first_limit (int): character limit for first message
            other_limits (int): character limit for other message

        Returns:
            List[str]: _description_
        """
        splited_texts = list()
        while True:
            if splited_texts:
                limit = other_limits
            else:
                limit = first_limit

            if len(text) > limit:
                space_index: int = text[:limit].rfind(' ')
                if space_index == -1:
                    space_index = limit # if text without spaces
                splited_texts.append(text[:space_index])
                text = text[space_index:].strip()
            else:
                splited_texts.append(text)
                return splited_texts