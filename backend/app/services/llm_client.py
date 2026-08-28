"""
Unified Google GenAI Client and LLM Integration for CompliSure.
Provides safe client instantiation, key validation, and fast-failover to local deterministic engines.
"""
from typing import Optional
from backend.app.config import settings
from backend.app.utils.logging import logger

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GenAIClientManager:
    """Manages connection to Google GenAI API with graceful offline fallback."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GenAIClientManager, cls).__new__(cls)
            cls._instance._client = None
            cls._instance._remote_available = None  # None = untested, True = working, False = offline
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        """Initializes the Google GenAI SDK client if valid API key is present."""
        api_key = settings.GEMINI_API_KEY
        if not HAS_GENAI or not self.is_valid_key(api_key):
            self._client = None
            self._remote_available = False
            return

        try:
            self._client = genai.Client(api_key=api_key.strip())
            # We will test on first call or keep as active
            self._remote_available = True
            logger.info(f"Initialized Google GenAI Client with model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.warning(f"Could not initialize Google GenAI Client: {e}. Using deterministic engine.")
            self._client = None
            self._remote_available = False

    @staticmethod
    def is_valid_key(key: Optional[str]) -> bool:
        """Validates API key format."""
        if not key:
            return False
        k = key.strip()
        if len(k) < 20:
            return False
        if k.startswith(("your_", "test_", "mock_", "dummy_", "placeholder_")):
            return False
        return True

    @property
    def client(self) -> Optional[object]:
        if self._remote_available is False:
            return None
        return self._client

    @property
    def is_remote_active(self) -> bool:
        return bool(self._client and self._remote_available)

    def mark_remote_failed(self, error: Exception):
        """Disables remote calls for the session after a failure to avoid latency spikes."""
        if self._remote_available is not False:
            logger.info(f"Gemini API remote call encountered ({error}). Switching to local deterministic engine.")
            self._remote_available = False


genai_manager = GenAIClientManager()
