# The definition here is only to make the type of configuration items obvious.
# Because we are operating on dataclasses, the initialization order precludes us from having some default initialized
# value, which is a real shame (though understandable)

class ConfigItem:
    id: str
