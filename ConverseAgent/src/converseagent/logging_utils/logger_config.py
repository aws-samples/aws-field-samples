import logging


def setup_logging() -> None:
    # Initialize logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not root_logger.handlers:
        # Create console handler and set level
        handler = logging.StreamHandler()

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        root_logger.addHandler(handler)


def setup_logger(name: str) -> logging.Logger:
    # Ensure root logging is configured
    if not logging.getLogger().handlers:
        setup_logging()

    logger = logging.getLogger(name)

    return logger
