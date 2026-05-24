import json
import logging
import os
import sys
from datetime import datetime, timezone

from src.infrastructure.config.env import EnvironSettings


class JsonFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = EnvironSettings()
        self._indent = 4 if settings.ENVIRONMENT == "development" else None

    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, indent=self._indent)


logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.propagate = False
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
