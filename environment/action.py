from environment.tag import TagList
from utils.singleton import Singleton


class Action:
    def __init__(self, *tags, id = None, content = None):
        self._id = id
        self._content = content
        self._tags = []
        for tag in tags[:9]:
            x = TagList().add_tag(tag, self)
            self._tags.append(x)

    @property
    def tags(self):
        return self._tags

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    def get_values(self, prefix = ""):
        return [x.value for x in self._tags if x.is_prefixed_by(prefix)]

    def set_id(self, id):
        self._id = id

    def set_content(self, content):
        self._content = content


class ActionList(metaclass=Singleton):
    def __init__(self):
        self._actions = []

    def add_action(self, action: Action):
        self._actions.append(action)
        # Actions have id 1-indexed this way
        action.set_id(len(self._actions))

    def get_actions(self, prefix: str = ""):
        root = TagList().get_tags(prefix)
        return root.nested_refs