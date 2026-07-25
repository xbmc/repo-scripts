from typing import TypedDict


class Attribute(TypedDict):
    """
    Represents the `data.attributes` field in the payload, which is used to store session, execution scope information,
    and other key-value pairs.
    """
    key: str
    value: str
