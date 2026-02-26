"""
tests/test_setup.py
===================
Phase 2A Validation Test
------------------------
Verifies that:
  1. All required packages are importable.
  2. The .env file exists and contains AWS credentials.
  3. AWSConfig loads correctly (credentials, model IDs, category constants).
  4. boto3 can construct a Bedrock-runtime client without raising.

Run with:
    source venv/Scripts/activate   # activate venv
    pytest tests/test_setup.py -v
"""

import importlib
import os
import sys
import types

import pytest

# Make sure the project root is on sys.path so we can import backend.*
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Package availability
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "boto3",
    "botocore",
    "faiss",          # faiss-cpu exposes as 'faiss'
    "langchain",
    "langchain_community",
    "PIL",            # Pillow
    "fitz",           # PyMuPDF
    "numpy",
    "pandas",
    "dotenv",         # python-dotenv
    "httpx",
    "pytest",
]


@pytest.mark.parametrize("package", REQUIRED_PACKAGES)
def test_package_importable(package: str) -> None:
    """Each required package must be importable in the active venv."""
    mod = importlib.import_module(package)
    assert isinstance(mod, types.ModuleType), f"{package} did not return a module"


# ─────────────────────────────────────────────────────────────────────────────
# 2. .env file exists
# ─────────────────────────────────────────────────────────────────────────────

def test_env_file_exists() -> None:
    """
    .env must exist at the project root.  If it is missing, copy
    .env.example and fill in real AWS credentials.
    """
    env_path = os.path.join(ROOT, ".env")
    assert os.path.isfile(env_path), (
        ".env file not found.  "
        "Copy .env.example → .env and fill in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. AWSConfig loads correctly
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def aws_config():
    """Import (and therefore instantiate) the AWSConfig singleton."""
    from backend.config import config  # triggers __init__ → _validate()
    return config


def test_config_loads(aws_config) -> None:
    """AWSConfig singleton should be importable without raising."""
    assert aws_config is not None


def test_config_aws_region(aws_config) -> None:
    """AWS region should be a non-empty string (defaults to us-east-1)."""
    assert isinstance(aws_config.aws_region, str)
    assert len(aws_config.aws_region) > 0


def test_config_embed_model(aws_config) -> None:
    """Titan embed model ID should contain 'titan-embed'."""
    assert "titan-embed" in aws_config.bedrock_embed_model.lower()


def test_config_llm_model(aws_config) -> None:
    """LLM model ID should reference Claude 3.5 Sonnet."""
    assert "claude-3-5-sonnet" in aws_config.bedrock_llm_model.lower()


def test_config_vector_store_path(aws_config) -> None:
    """vector_store_path should be a non-empty string."""
    assert isinstance(aws_config.vector_store_path, str)
    assert len(aws_config.vector_store_path) > 0


def test_config_retrieval_params(aws_config) -> None:
    """top_k_results and similarity_threshold should be sensible defaults."""
    assert isinstance(aws_config.top_k_results, int)
    assert aws_config.top_k_results > 0

    assert isinstance(aws_config.similarity_threshold, float)
    assert 0.0 < aws_config.similarity_threshold < 1.0


def test_config_category_constants(aws_config) -> None:
    """The three Semantic Router category constants must be present."""
    assert aws_config.CATEGORY_ERROR_CODES == "ERROR_CODES"
    assert aws_config.CATEGORY_SCHEMATICS == "SCHEMATICS"
    assert aws_config.CATEGORY_GENERAL == "GENERAL"


def test_config_boto3_session_kwargs(aws_config) -> None:
    """get_boto3_session_kwargs() must return a dict with the three expected keys."""
    kwargs = aws_config.get_boto3_session_kwargs()
    assert isinstance(kwargs, dict)
    assert "aws_access_key_id" in kwargs
    assert "aws_secret_access_key" in kwargs
    assert "region_name" in kwargs
    # Keys must not be None / empty
    assert kwargs["aws_access_key_id"]
    assert kwargs["aws_secret_access_key"]
    assert kwargs["region_name"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. boto3 Bedrock client construction (no live API call)
# ─────────────────────────────────────────────────────────────────────────────

def test_bedrock_client_construction(aws_config) -> None:
    """
    get_bedrock_client() should return a boto3 client object without
    making any network calls (credentials are validated locally by botocore).
    """
    client = aws_config.get_bedrock_client()
    # The client's service model name should be 'bedrock-runtime'
    assert client.meta.service_model.service_name == "bedrock-runtime"
