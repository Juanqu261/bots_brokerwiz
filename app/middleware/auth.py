"""
Autenticación Bearer Token para la API.

Middleware simple que valida el token en el header Authorization.
El token se configura en API_KEY (settings).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.settings import settings

# Esquema de seguridad Bearer
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Token de autenticación para acceso a la API"
)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependencia para validar Bearer token en endpoints protegidos.
    
    Uso:
        @router.post("/cotizaciones")
        async def crear_cotizacion(
            data: JobCreate,
            token: str = Depends(verify_token)
        ):
            ...
    
    Raises:
        HTTPException 401: Token inválido o faltante
    
    Returns:
        El token validado (por si se necesita para logging)
    """
    token = credentials.credentials
    
    if token != settings.api.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token


# Alias para usar en dependencias
require_auth = Depends(verify_token)
