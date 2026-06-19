from pydantic_settings import BaseSettings

class Config(BaseSettings):
    threshold: float = 100.0
    model: str = "gemini-2.5-flash"

config = Config()
