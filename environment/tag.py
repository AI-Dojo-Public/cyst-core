from utils.singleton import Singleton


class Tag:
    def __init__(self, name, prefix = "", value = 1, depth = 0):
        self._name = name
        self._prefix = prefix
        self._value = value
        self._depth = depth
        self._children = []
        self._ref = None

    @classmethod
    def from_string(cls, name: str):
        items = name.split(":")
        tag = cls(items[0])
        tag.add_children(items[1:])
        return tag

    @property
    def value(self):
        return self._value

    @property
    def name(self):
        return self._prefix + ":" + self._name

    @property
    def name_list(self):
        result = self._prefix.split(":")
        result.append(self._name)
        return result

    def set_ref(self, ref):
        self._ref = ref

    @property
    def ref(self):
        return self._ref

    def _nested_refs(self, result: []):
        if self._ref:
            result.append(self._ref)
        for child in self._children:
            if isinstance(child, Tag):
                child._nested_refs(result)

    @property
    def nested_refs(self):
        result = []
        self._nested_refs(result)
        return result

    def is_prefixed_by(self, prefix: str):
        if not prefix or prefix == self.name:
            return True

        if self.name.startswith(prefix + ":"):
            return True

        return False

    def add_children(self, name, ref):
        if not name:
            return

        if self._depth == 3:
            raise Exception("Could not nest tags deeper than four levels")

        if isinstance(name, str):
            items = name.split(":")
        else:
            items = name

        head = items[0]
        tail = None
        if len(items) > 1:
            tail = items[1:]

        index = -1
        for i, x in enumerate(self._children):
            if isinstance(x, Tag) and x._name == head:
                index = i
                break

        if index == -1:
            child_name = head
            child_depth = self._depth + (1 if self._name != "_" else 0)
            child_index = len(self._children)
            child_value = self._value + ((child_index + 1) << (8 * child_depth))

            if self._name == "_":
                child_prefix = ""
            elif not self._prefix:
                child_prefix = self._name
            else:
                child_prefix = self._prefix + ":" + self._name

            child = Tag(child_name, child_prefix, child_value, child_depth)
            self._children.append(child)
            index = child_index

        if tail:
            return self._children[index].add_children(tail, ref)
        else:
            self._children[index].set_ref(ref)
            return self._children[index]

    def _get_children(self, names: []):
        if not names or not names[0]:
            return self

        for child in self._children:
            if isinstance(child, Tag) and child._name == names[0]:
                return child._get_children(names[1:])

        return None

    def get_children(self, name: str):
        items = name.split(":")
        return self._get_children(items)


class TagList(metaclass=Singleton):
    def __init__(self):
        self._tags = Tag("_", "", 0, 0)

    def add_tag(self, name: str, ref):
        return self._tags.add_children(name, ref)

    def get_tags(self, prefix: str):
        return self._tags.get_children(prefix)