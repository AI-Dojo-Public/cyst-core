# The definition here is only to make the type of configuration items obvious.
# Because we are operating on dataclasses, the initialization order precludes us from having some default initialized
# value, which is a real shame (though understandable)
import dataclasses
import uuid
from typing import Any

"""
Provides an API to configure all aspects of the simulation engine.

Available to: creator, models
Hidden from:  agents
"""


class ConfigItem:
    """
    A superclass of a configuration items.
    """
    id: str
