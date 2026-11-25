import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 5000
    db_host: str = "db"
    db_port: int = 3306
    db_name: str = "taskmgr"
    db_user: str = "taskmgr"
    db_password: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            host=os.getenv("APP_HOST", cls.host),
            port=int(os.getenv("APP_PORT", cls.port)),
            db_host=os.getenv("DB_HOST", cls.db_host),
            db_port=int(os.getenv("DB_PORT", cls.db_port)),
            db_name=os.getenv("DB_NAME", cls.db_name),
            db_user=os.getenv("DB_USER", cls.db_user),
            db_password=os.getenv("DB_PASSWORD", cls.db_password),
        )
