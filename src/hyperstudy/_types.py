"""Enums for the HyperStudy API.

All enums inherit from (str, Enum) so users can pass either
Scope.EXPERIMENT or the plain string "experiment".
"""

from enum import Enum


class Scope(str, Enum):
    EXPERIMENT = "experiment"
    ROOM = "room"
    PARTICIPANT = "participant"


class DataType(str, Enum):
    EVENTS = "events"
    RECORDINGS = "recordings"
    CHAT = "chat"
    VIDEOCHAT = "videochat"
    SYNC = "sync"
    RATINGS = "ratings"
    COMPONENTS = "components"
    PARTICIPANTS = "participants"
    ROOMS = "rooms"


class RatingKind(str, Enum):
    CONTINUOUS = "continuous"
    SPARSE = "sparse"
