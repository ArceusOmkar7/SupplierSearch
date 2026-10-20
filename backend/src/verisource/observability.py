"""Emit structured operational metadata without request bodies, URLs or credentials."""

import json
import logging
from datetime import UTC, datetime

LOGGER = logging.getLogger("verisource")


def record_request(request_id: str, method: str, status: int) -> None:
    LOGGER.info(
        json.dumps(
            {
                "at": datetime.now(UTC).isoformat(),
                "event": "http.completed",
                "request_id": request_id,
                "method": method,
                "status": status,
            }
        )
    )
