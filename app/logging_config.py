import logging
import sys

from app.config import settings


def setup_logging() -> None:
    level = logging.DEBUG if not settings.is_production else logging.WARNING
    if settings.log_level:
        level = getattr(logging, settings.log_level.upper(), level)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "llama_index"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
