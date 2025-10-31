from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    FRESH_DOMAIN: str = Field()
    FRESH_KEY: str = Field()
    FRESH_TEMPLATE_FILEPATH: str = Field()
    FRESH_PAGE_SIZE: int = Field()
    FRESH_WORKSPACE_ID: int = Field()

    FRESH_DEFAULT_CONTACT_EMAIL: str = Field()
    FRESH_DEFAULT_DEPT_ID: int = Field()
    FRESH_DEFAULT_GROUP_ID: int = Field()
    FRESH_DEFAULT_CATEGORY: str = Field()
    FRESH_DEFAULT_SUBJECT: str = Field()

    MAX_REQUEST_TIMEOUT: int = Field()
    MAX_REQUEST_RETRIES: int = Field()

    VERBOSE: bool = Field()

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
