from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    corpus_dir: str = 'corpus/private'
    database_url: str = 'sqlite:///data/exampilot.db'
    llm_provider: str = 'extractive'
    llm_model: str = ''
    llm_api_key: str = ''
    llm_base_url: str = 'https://api.openai.com/v1'
    embedding_provider: str = 'sentence_transformers'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    vision_provider: str = 'local'
    vision_model: str = ''
    vision_api_key: str = ''
    app_env: str = 'development'

    @property
    def corpus(self):
        return (ROOT / self.corpus_dir).resolve()

    @property
    def db_path(self):
        if not self.database_url.startswith('sqlite:///'):
            raise ValueError('Only sqlite:/// database URLs are supported')
        return (ROOT / self.database_url.removeprefix('sqlite:///')).resolve()


settings = Settings()
