from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


def _assume_utc(value: datetime) -> datetime:
    # timestamps are written in UTC, but SQLite returns them without tzinfo
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


UTCDateTime = Annotated[datetime, AfterValidator(_assume_utc)]
