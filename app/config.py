from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./toxic_chat.db"
    model_path: str = "ml/toxic_svm_pipeline.joblib"

    player_api_keys: str = "player-dev-key-1"
    moderator_api_keys: str = "moderator-dev-key-1"
    admin_api_keys: str = "admin-dev-key-1"

    player_rate_limit: int = 60
    moderator_rate_limit: int = 300

    model_config = {"env_file": ".env"}

    def get_player_keys(self) -> set[str]:
        return {k.strip() for k in self.player_api_keys.split(",")}

    def get_moderator_keys(self) -> set[str]:
        return {k.strip() for k in self.moderator_api_keys.split(",")}

    def get_admin_keys(self) -> set[str]:
        return {k.strip() for k in self.admin_api_keys.split(",")}


@lru_cache
def get_settings() -> Settings:
    return Settings()
