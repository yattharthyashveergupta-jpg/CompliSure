"""
Safeguard Configuration Endpoints.
Allows viewing and tuning active evidence thresholds, verification policies, and retrieval depth.
"""
from fastapi import APIRouter, status
from backend.app.models.schemas import SafeguardConfig, SafeguardMode
from backend.app.config import settings
from backend.app.utils.logging import logger

router = APIRouter(prefix="/safeguards", tags=["Safeguards"])

# In-memory runtime active config
_active_config = SafeguardConfig(
    evidence_threshold=settings.DEFAULT_EVIDENCE_THRESHOLD,
    require_source_citation=settings.REQUIRE_SOURCE_CITATION,
    enable_answer_verification=settings.ENABLE_ANSWER_VERIFICATION,
    allow_unsupported_answers=settings.ALLOW_UNSUPPORTED_ANSWERS,
    default_mode=SafeguardMode(settings.DEFAULT_SAFEGUARD_MODE),
    top_k=settings.DEFAULT_TOP_K,
    min_supporting_chunks=settings.MIN_SUPPORTING_CHUNKS,
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP
)


@router.get(
    "",
    response_model=SafeguardConfig,
    summary="Get active safeguard configuration"
)
def get_safeguard_config():
    """Retrieves current evidence thresholds, verification policies, and active safeguard mode."""
    return _active_config


@router.post(
    "/configure",
    response_model=SafeguardConfig,
    status_code=status.HTTP_200_OK,
    summary="Update safeguard parameters"
)
def update_safeguard_config(config: SafeguardConfig):
    """Dynamically updates evidence threshold, citation requirements, and verification parameters."""
    global _active_config
    _active_config = config
    
    # Sync with global settings
    settings.DEFAULT_EVIDENCE_THRESHOLD = config.evidence_threshold
    settings.REQUIRE_SOURCE_CITATION = config.require_source_citation
    settings.ENABLE_ANSWER_VERIFICATION = config.enable_answer_verification
    settings.ALLOW_UNSUPPORTED_ANSWERS = config.allow_unsupported_answers
    settings.DEFAULT_SAFEGUARD_MODE = config.default_mode.value
    settings.DEFAULT_TOP_K = config.top_k
    settings.MIN_SUPPORTING_CHUNKS = config.min_supporting_chunks
    settings.CHUNK_SIZE = config.chunk_size
    settings.CHUNK_OVERLAP = config.chunk_overlap

    logger.info(
        f"Updated Safeguards | Threshold: {config.evidence_threshold:.2f} | "
        f"Verification: {config.enable_answer_verification} | Min Chunks: {config.min_supporting_chunks} | Default Mode: {config.default_mode}"
    )
    return _active_config
