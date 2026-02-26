"""
FastAPI Main Application for Mistri.AI
Provides REST API endpoints for hardware repair diagnosis using RAG.
"""
import logging
from typing import Optional
from io import BytesIO

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image

import re
from backend.rag_retrieve import search_manual
from backend.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mistri.AI API",
    description="Stack Overflow for Hardware Repair - RAG-powered diagnosis",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response Models
class DiagnosisResponse(BaseModel):
    """Response model matching the system persona format."""
    diagnosis: str
    safety_warning: str
    steps: list[str]
    matched_errors: list[dict]
    confidence_score: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        message="Mistri.AI API is running"
    )



def detect_intent(text: str, has_image: bool) -> Optional[str]:
    """
    Detect user intent to route to appropriate category.
    
    **INTENT-BASED ROUTING LOGIC**:
    - Image uploaded → SCHEMATICS
    - Error code pattern (e.g., "IE", "DE", "UE") → ERROR_CODES
    - Default → None (search all categories)
    
    Args:
        text: User's query text
        has_image: Whether user uploaded an image
        
    Returns:
        Category string or None
    """
    # If image is uploaded, assume schematic/board repair intent
    if has_image:
        logger.info("Intent detected: SCHEMATICS (image uploaded)")
        return config.CATEGORY_SCHEMATICS
    
    # Check for error code pattern in text (1-3 uppercase letters, optional digit)
    # Examples: IE, DE, UE, dE, dE1, dE2, PE, LE, EE, PF
    error_code_pattern = r'\b[A-Z]{1,3}\d?\b'
    if re.search(error_code_pattern, text.upper()):
        logger.info("Intent detected: ERROR_CODES (error code pattern found)")
        return config.CATEGORY_ERROR_CODES
    
    # Check for error-related keywords
    error_keywords = ['error', 'code', 'display', 'showing', 'flashing']
    if any(keyword in text.lower() for keyword in error_keywords):
        logger.info("Intent detected: ERROR_CODES (error keywords found)")
        return config.CATEGORY_ERROR_CODES
    
    # Default: search all categories
    logger.info("Intent detected: None (searching all categories)")
    return None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status of the API
    """
    try:
        # TODO: Add checks for:
        # - Bedrock connectivity
        # - Aurora database connection
        # - FAISS index availability
        
        return HealthResponse(
            status="healthy",
            message="All systems operational"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    text: str = Form(..., description="User's problem description"),
    image: Optional[UploadFile] = File(None, description="Optional image of the issue")
):
    """
    Main diagnosis endpoint.
    
    Accepts a text description and optional image, performs RAG search,
    and returns a structured diagnosis following the "Senior Mistri" persona.
    
    Args:
        text: User's problem description (e.g., "washing machine not draining")
        image: Optional image file
        
    Returns:
        DiagnosisResponse with matched errors and repair guidance
        
    Example:
        ```bash
        curl -X POST http://localhost:8000/diagnose \\
             -F "text=washing machine not draining" \\
             -F "image=@photo.jpg"
        ```
    """
    try:
        logger.info(f"Received diagnosis request: {text}")
        
        # Process image if provided
        image_bytes = None
        if image:
            try:
                # Read and validate image
                contents = await image.read()
                img = Image.open(BytesIO(contents))
                logger.info(f"Received image: {img.format} {img.size}")
                image_bytes = contents
            except Exception as e:
                logger.warning(f"Failed to process image: {e}")
                # Continue without image
        
        # Detect user intent for category-based filtering
        intent_category = detect_intent(text, has_image=image is not None)
        
        # Perform RAG search with category filtering
        try:
            matches = search_manual(
                query_text=text,
                query_image_bytes=image_bytes,
                intent_category=intent_category,  # THE TREE ROUTER
                top_k=3
            )
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Search failed: {str(e)}"
            )
        
        if not matches:
            raise HTTPException(
                status_code=404,
                detail="No matching error codes found. Please provide more details."
            )
        
        # Format response following "Senior Mistri" persona
        top_match = matches[0]
        
        # Generate diagnosis text
        diagnosis = (
            f"The {top_match['code']} error means: {top_match['name']}. "
            f"{top_match['description']}"
        )
        
        # Safety warning (always remind to unplug)
        safety_warning = (
            "⚠️ SAFETY FIRST: Unplug the machine from power! "
            "Wait 2-3 minutes for capacitors to discharge before opening."
        )
        
        # Generate repair steps based on error type
        steps = generate_repair_steps(top_match)
        
        # Calculate confidence based on similarity score
        confidence = top_match.get('similarity_score', 0.0)
        
        response = DiagnosisResponse(
            diagnosis=diagnosis,
            safety_warning=safety_warning,
            steps=steps,
            matched_errors=[
                {
                    'code': m['code'],
                    'name': m['name'],
                    'similarity': m.get('similarity_score', 0.0)
                }
                for m in matches
            ],
            confidence_score=confidence
        )
        
        logger.info(f"Diagnosis complete: {top_match['code']} (confidence: {confidence:.2f})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def generate_repair_steps(error_match: dict) -> list[str]:
    """
    Generate repair steps based on error code.
    
    Args:
        error_match: Matched error code dictionary
        
    Returns:
        List of repair steps
        
    TODO: Enhance with LLM generation using Claude 3 Sonnet
    """
    code = error_match['code']
    
    # Basic step templates (will be enhanced with LLM later)
    step_templates = {
        'IE': [
            "Check the water inlet valve for blockages",
            "Inspect the inlet hose for kinks or damage",
            "Verify water pressure is adequate (min 20 PSI)",
            "Test the water level sensor"
        ],
        'UE': [
            "Redistribute the load evenly in the drum",
            "Check if the machine is level (use a spirit level)",
            "Reduce the load size if overloaded",
            "Inspect shock absorbers for wear"
        ],
        'DE': [
            "Check the drain hose for clogs",
            "Inspect the drain pump filter (usually at bottom front)",
            "Test the drain pump motor",
            "Verify drain hose is not kinked"
        ],
        'FE': [
            "Turn off water supply immediately",
            "Check water inlet valve for failure (stuck open)",
            "Inspect pressure sensor connection",
            "Test the main control board"
        ],
        'dE': [
            "Ensure door is fully closed and latched",
            "Check door seal for obstructions",
            "Inspect door lock assembly",
            "Test door switch continuity with multimeter"
        ]
    }
    
    # Return specific steps or generic ones
    return step_templates.get(code, [
        "Refer to the error description above",
        "Check all electrical connections",
        "Inspect for visible damage or wear",
        "Consider calling a professional if unsure"
    ])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again."
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
