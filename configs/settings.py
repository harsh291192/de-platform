# ── configs/settings.py ───────────────────────────────────────────
# Central config loader — use this everywhere
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All configuration loaded from environment variables.
    Never hardcode values — always load from env.
    """

    # AWS
    aws_access_key_id: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_DEFAULT_REGION")
    s3_bucket_raw: str = Field(env="S3_BUCKET_RAW")
    s3_bucket_processed: str = Field(env="S3_BUCKET_PROCESSED")

    # Snowflake
    snowflake_account: str = Field(env="SNOWFLAKE_ACCOUNT")
    snowflake_user: str = Field(env="SNOWFLAKE_USER")
    snowflake_password: str = Field(env="SNOWFLAKE_PASSWORD")
    snowflake_database: str = Field(default="analytics", env="SNOWFLAKE_DATABASE")
    snowflake_warehouse: str = Field(default="compute_wh", env="SNOWFLAKE_WAREHOUSE")

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS"
    )

    # App
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Singleton — loaded once, cached forever."""
    return Settings()


# Usage in any file:
# from configs.settings import get_settings
# settings = get_settings()
# conn = snowflake.connector.connect(account=settings.snowflake_account, ...)
