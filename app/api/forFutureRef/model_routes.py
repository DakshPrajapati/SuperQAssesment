from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import thread_crud
from app.services.thread_service import ThreadService
from app.schemas.thread_schemas import (
    ThreadCreate,
    ThreadResponse,
    Thread as ThreadSchema,
    SummaryResponse,
    ModelMetadataResponse,
    ModelMetadataCreate
)
from app.schemas.message_schemas import MessageCreate, MessageResponse
from app.core.models import get_model_config, get_available_models
from typing import List, Dict, Any

router = APIRouter(prefix="/models", tags=["threads"])
thread_service = ThreadService()

@router.post(
    "/add",
    response_model=ModelMetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update model metadata",
    tags=["model-metadata"]
)
async def create_or_update_model(
    metadata: ModelMetadataCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update metadata for an LLM model.
    
    **Parameters:**
    - **model_name**: Model identifier (e.g., "google/gemini-pro")
    - **summary_type**: Summary size preference ('small', 'medium', 'large')
    - **max_tokens**: Maximum tokens the model supports
    - **description**: Optional model description
    
    **Example:**
    ```json
    {
        "model_name": "google/gemini-pro",
        "summary_type": "medium",
        "max_tokens": 4096,
        "description": "Google's Gemini Pro model"
    }
    ```
    
    **Returns:**
    - 201: Model metadata created/updated successfully
    - 422: Invalid request data
    """
    return thread_crud.create_or_update_model_metadata(
        db=db,
        model_name=metadata.model_name,
        summary_type=metadata.summary_type,
        max_tokens=metadata.max_tokens,
        description=metadata.description
    )





@router.get(
    "/",
    response_model=List[ModelMetadataResponse],
    summary="List all model metadata",
    tags=["model-metadata"]
)
async def list_models(db: Session = Depends(get_db)):
    """
    Get metadata for all registered models.
    
    **Returns:**
    - 200: List of all model metadata
    """
    return thread_crud.get_all_model_metadata(db)


@router.get(
    "/{model_name}",
    response_model=ModelMetadataResponse,
    summary="Get specific model metadata",
    tags=["model-metadata"],
    responses={
        200: {"description": "Model metadata found"},
        404: {"description": "Model not found"}
    }
)
async def get_model(model_name: str, db: Session = Depends(get_db)):
    """
    Get metadata for a specific model.
    
    **Parameters:**
    - **model_name**: The model identifier
    
    **Returns:**
    - 200: Model metadata
    - 404: Model not found
    """
    metadata = thread_crud.get_model_metadata(db, model_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found"
        )
    return metadata


@router.delete(
    "/{model_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete model metadata",
    tags=["model-metadata"],
    responses={
        204: {"description": "Model metadata deleted"},
        404: {"description": "Model not found"}
    }
)
async def delete_model(model_name: str, db: Session = Depends(get_db)):
    """
    Delete metadata for a specific model.
    
    **Parameters:**
    - **model_name**: The model identifier
    
    **Returns:**
    - 204: Model metadata deleted
    - 404: Model not found
    """
    deleted = thread_crud.delete_model_metadata(db, model_name)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found"
        )
    return None