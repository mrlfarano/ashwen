import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_session
from app.models import Credential
from app.schemas import CredentialSet, CredentialStatusResponse, CredentialStoredResponse, DeleteResponse
from app.services.encryption import encrypt_value

router = APIRouter(prefix="/credentials", tags=["credentials"])
logger = logging.getLogger(__name__)

# Valid credential providers
VALID_PROVIDERS = {"openai", "anthropic", "ollama"}


@router.get("/", response_model=list[str])
async def list_providers(session: AsyncSession = Depends(get_session)):
    """
    List all configured credential providers.
    
    Returns:
        List[str]: List of provider names that have credentials configured
        
    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        result = await session.execute(select(Credential.provider))
        providers = [row[0] for row in result.all()]
        
        logger.info(f"Listed {len(providers)} configured credential providers")
        return providers
        
    except SQLAlchemyError as e:
        logger.error(f"Database error listing credential providers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credential providers from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing credential providers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing credential providers"
        )


@router.post("/{provider}", status_code=status.HTTP_200_OK, response_model=CredentialStoredResponse)
async def set_credential(
    provider: str,
    payload: CredentialSet,
    session: AsyncSession = Depends(get_session),
):
    """
    Set or update an API credential for a provider.
    
    Args:
        provider: Provider name (openai, anthropic, ollama)
        payload: Credential data containing the API key
        
    Returns:
        dict: Confirmation of credential storage
        
    Raises:
        HTTPException: 422 if provider name or API key is invalid
        HTTPException: 500 if database operation or encryption fails
    """
    # Validate provider
    if not provider or not provider.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provider name is required"
        )
    
    provider = provider.strip().lower()
    
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid provider '{provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )
    
    # Validate API key
    if not payload.api_key or not payload.api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key is required and cannot be empty"
        )
    
    try:
        # Encrypt the API key
        try:
            encrypted = encrypt_value(payload.api_key.strip())
        except Exception as e:
            logger.error(f"Encryption error for provider {provider}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to encrypt API key. Please check encryption configuration."
            )
        
        # Check if credential already exists
        result = await session.execute(select(Credential).where(Credential.provider == provider))
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.encrypted_key = encrypted
            logger.info(f"Updated credential for provider: {provider}")
        else:
            credential = Credential(provider=provider, encrypted_key=encrypted)
            session.add(credential)
            logger.info(f"Created credential for provider: {provider}")
        
        await session.commit()
        
        return {
            "provider": provider,
            "stored": True,
            "action": "updated" if existing else "created"
        }
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error setting credential for provider {provider}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store credential in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error setting credential for provider {provider}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while storing the credential"
        )


@router.get("/{provider}", response_model=CredentialStatusResponse)
async def has_credential(provider: str, session: AsyncSession = Depends(get_session)):
    if not provider or not provider.strip():
        raise HTTPException(status_code=422, detail="Provider name is required")

    provider = provider.strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider '{provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )

    result = await session.execute(select(Credential).where(Credential.provider == provider))
    credential = result.scalar_one_or_none()
    return {"provider": provider, "configured": credential is not None}


@router.delete("/{provider}", response_model=DeleteResponse)
async def delete_credential(provider: str, session: AsyncSession = Depends(get_session)):
    if not provider or not provider.strip():
        raise HTTPException(status_code=422, detail="Provider name is required")

    provider = provider.strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider '{provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )

    result = await session.execute(select(Credential).where(Credential.provider == provider))
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(404, "Credential not found")
    await session.delete(credential)
    await session.commit()
    return {"deleted": True}
