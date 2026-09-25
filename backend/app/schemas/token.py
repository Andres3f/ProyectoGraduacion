from pydantic import BaseModel


class Token(BaseModel):
    """Token de acceso JWT devuelto al autenticarse."""
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """Par de tokens JWT: acceso (corta vida) + refresco (larga vida)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Entrada para renovar el access_token usando el refresh_token."""
    refresh_token: str


class TokenData(BaseModel):
    """Payload decodificado del JWT (claims de identidad y rol)."""
    email: str | None = None
    role: str | None = None


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""
    email: str
    password: str
