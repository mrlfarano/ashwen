from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "Ashwen"
    app_version: str = "0.1.0"
    debug: bool = True

    database_url: str = ""
    data_dir: str = Field(default="", validation_alias="ASHWEN_DATA_DIR")
    encryption_key: str = ""

    # Database connection pooling settings
    db_pool_size: int = Field(default=5, description="Connection pool size (not used with SQLite)")
    db_max_overflow: int = Field(default=10, description="Max connections beyond pool_size (not used with SQLite)")
    db_pool_timeout: int = Field(default=30, description="Seconds to wait for connection from pool")
    db_pool_recycle: int = Field(default=3600, description="Recycle connections after N seconds")
    db_pool_pre_ping: bool = Field(default=True, description="Test connection health before use")

    ollama_base_url: str = "http://192.168.50.4:11434"


settings = Settings()


def get_data_dir() -> Path:
    if settings.data_dir:
        data_dir = Path(settings.data_dir)
    else:
        data_dir = Path.cwd()

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_database_url() -> str:
    if settings.database_url:
        return settings.database_url

    db_path = get_data_dir() / "ashwen.db"
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def get_encryption_key() -> bytes:
    key = settings.encryption_key
    if not key:
        key_path = get_data_dir() / ".encryption_key"
        if key_path.exists():
            key = key_path.read_text().strip()
        else:
            from cryptography.fernet import Fernet

            key = Fernet.generate_key().decode()
            key_path.write_text(key)
    return key.encode() if isinstance(key, str) else key
