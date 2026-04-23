import os


class SecretError(RuntimeError):
    """Raised when a required secret is missing or malformed."""


def get_secret(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def get_required_secret(name: str) -> str:
    value = get_secret(name)
    if not value:
        raise SecretError(f"Missing required secret: {name}")
    return value


def get_bool_secret(name: str, default: bool = False) -> bool:
    value = get_secret(name)
    if value is None or value == "":
        return default

    normalized = value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise SecretError(
        f"Invalid boolean value for secret {name}: {value!r}. "
        "Use one of: true/false, 1/0, yes/no, on/off."
    )