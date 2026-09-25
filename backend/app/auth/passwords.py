import bcrypt


def hash_password(password: str) -> str:
    """Genera un hash bcrypt para la contraseña en texto plano."""
    # Codifica a UTF-8, genera una sal aleatoria y devuelve el hash como texto.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra un hash bcrypt (mismo formato $2b$)."""
    try:
        # bcrypt compara en tiempo constante; no acepta hashes mal formados.
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Hash inválido (longitud/formato incorrecto) se trata como contraseña errónea.
        return False
