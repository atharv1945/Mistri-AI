"""
backend/config.py
=================
AWS + Bedrock configuration for Mistri.AI.

Loads all settings from a .env file (or real environment).
All downstream modules import the `config` singleton — never
instantiate AWSConfig directly.

Required .env variables:
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY

Optional .env overrides (sensible defaults are provided):
    AWS_REGION                 (default: us-east-1)
    BEDROCK_EMBED_MODEL        (default: amazon.titan-embed-text-v2:0)
    BEDROCK_LLM_MODEL          (default: anthropic.claude-3-5-sonnet-20240620-v1:0)
    VECTOR_STORE_PATH          (default: ./data/vector_store)
    TOP_K_RESULTS              (default: 3)
    SIMILARITY_THRESHOLD       (default: 0.6)
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root (or any parent directory)
load_dotenv()


class AWSConfig:
    """
    Singleton configuration class for Mistri.AI's AWS / Bedrock integration.

    Design notes
    ────────────
    • Singleton pattern: guarantees a single source-of-truth for credentials.
    • Validation on startup: fails fast if mandatory env vars are absent so
      the error surfaces at import time, not mid-request.
    • Category constants live here so every module uses the same strings
      (prevents category typos across the codebase).
    """

    _instance: Optional["AWSConfig"] = None

    def __new__(cls) -> "AWSConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # ── AWS Credentials ──────────────────────────────────────────────────
        self.aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")

        # ── Bedrock Model IDs ────────────────────────────────────────────────
        # Titan Embed Text v2 – produces 1 024-dim text embeddings.
        # NFR-001: keeps latency low by operating purely on text at retrieval time.
        self.bedrock_embed_model: str = os.getenv(
            "BEDROCK_EMBED_MODEL",
            "amazon.titan-embed-text-v2:0",
        )

        # Claude 3.5 Sonnet – reasoning / answer synthesis at the inference step.
        self.bedrock_llm_model: str = os.getenv(
            "BEDROCK_LLM_MODEL",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
        )

        # ── Local Vector Store (FAISS – Aurora mock) ─────────────────────────
        self.vector_store_path: str = os.getenv(
            "VECTOR_STORE_PATH",
            "./data/vector_store",
        )

        # ── Retrieval Parameters ─────────────────────────────────────────────
        self.top_k_results: int = int(os.getenv("TOP_K_RESULTS", "3"))
        self.similarity_threshold: float = float(
            os.getenv("SIMILARITY_THRESHOLD", "0.6")
        )

        # ── Semantic Router: Category Constants ──────────────────────────────
        # These are the metadata tags attached to every vector in the FAISS index.
        # The Tree Searcher (rag_retrieve.py) uses them to pre-filter results,
        # satisfying NFR-001 (low-latency category-scoped retrieval).
        self.CATEGORY_ERROR_CODES: str = "ERROR_CODES"
        self.CATEGORY_SCHEMATICS: str = "SCHEMATICS"
        self.CATEGORY_GENERAL: str = "GENERAL"

        # ── Validate ─────────────────────────────────────────────────────────
        self._validate()
        self._initialized = True

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _validate(self) -> None:
        """Raise ValueError at startup if mandatory credentials are missing."""
        missing: list[str] = []
        if not self.aws_access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if not self.aws_secret_access_key:
            missing.append("AWS_SECRET_ACCESS_KEY")

        if missing:
            raise ValueError(
                f"[Mistri.AI] Missing required environment variables: "
                f"{', '.join(missing)}. "
                f"Add them to your .env file and restart."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public helpers
    # ─────────────────────────────────────────────────────────────────────────

    def get_boto3_session_kwargs(self) -> dict:
        """
        Return a kwargs dict suitable for ``boto3.Session(**kwargs)``.

        Example
        -------
        >>> import boto3
        >>> session = boto3.Session(**config.get_boto3_session_kwargs())
        """
        return {
            "aws_access_key_id": self.aws_access_key_id,
            "aws_secret_access_key": self.aws_secret_access_key,
            "region_name": self.aws_region,
        }

    def get_bedrock_client(self):
        """
        Convenience factory: returns a ready-to-use ``bedrock-runtime`` client.

        Returns
        -------
        botocore.client.BedrockRuntime
        """
        import boto3  # local import so the module is importable without boto3

        session = boto3.Session(**self.get_boto3_session_kwargs())
        return session.client(service_name="bedrock-runtime")

    def __repr__(self) -> str:
        return (
            f"AWSConfig("
            f"region={self.aws_region!r}, "
            f"embed_model={self.bedrock_embed_model!r}, "
            f"llm_model={self.bedrock_llm_model!r}, "
            f"vector_store={self.vector_store_path!r}"
            f")"
        )


# ── Global singleton ──────────────────────────────────────────────────────────
# All backend modules should do:   from backend.config import config
config = AWSConfig()
