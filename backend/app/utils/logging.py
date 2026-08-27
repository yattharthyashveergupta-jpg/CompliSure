"""
Structured logging utility for CompliSure.
Provides clean, readable logs without leaking API keys or confidential text.
"""
import logging
import sys
from typing import Any, Dict


def setup_logger(name: str = "complisure") -> logging.Logger:
    """Configures and returns a logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger


logger = setup_logger()


def log_query_decision(
    question: str,
    mode: str,
    decision: str,
    evidence_status: str,
    verification: str,
    top_score: float,
    sources_count: int
):
    """Logs a compliance assistant query evaluation decision."""
    logger.info(
        f"Query Evaluated | Mode: {mode} | Decision: {decision} | "
        f"Evidence: {evidence_status} (Top Score: {top_score:.2f}, Sources: {sources_count}) | "
        f"Verification: {verification} | Question: '{question[:60]}...'"
    )
