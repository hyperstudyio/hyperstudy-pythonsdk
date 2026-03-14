"""HyperStudy Python SDK — access experiment data from notebooks and scripts.

Usage::

    import hyperstudy

    hs = hyperstudy.HyperStudy(api_key="hst_live_...")
    events = hs.get_events("experiment_id")
"""

from ._types import DataType, RatingKind, Scope
from .client import HyperStudy
from .exceptions import (
    AuthenticationError,
    ForbiddenError,
    HyperStudyError,
    NotFoundError,
    ServerError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "HyperStudy",
    "__version__",
    # Exceptions
    "HyperStudyError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "ServerError",
    "ValidationError",
    # Enums
    "Scope",
    "DataType",
    "RatingKind",
]
