import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # S3 Bucket Storage settings
    SUPABASE_S3_ENDPOINT: str        # https://<project-id>.supabase.co/storage/v1/s3
    SUPABASE_ACCESS_KEY_ID: str
    SUPABASE_SECRET_ACCESS_KEY: str
    SUPABASE_REGION: str
    SUPABASE_BUCKET: str

    # LLM settings
    OPENAI_API_KEY: str
    GROQ_API_KEY: str
    DEEPSEEK_API_KEY: str
    GEMINI_API_KEY: str


    # Tavily MCP settings
    TAVILY_MCP_LINK: str

    # Langchain/LangSmith settings
    LANGCHAIN_API_KEY: str
    LANGSMITH_TRACING: bool
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    LANGSMITH_ENDPOINT: str

    # Vector Store Pinecone settings
    PINECONE_INDEX_NAME: str
    PINECONE_API_KEY: str


    # Postgres DB settings
    SUPABASE_DB_URL: str


    # JWT Auth settings
    SECRET_KEY: str
    ALGORITHM: str
    EXPIRE_HOURS: int


    class Config:
        env_file = ".env"

settings = Settings()


# LangChain/LangSmith read tracing config from OS ENV VARS at runtime — NOT from
# this pydantic Settings object. pydantic-settings reads .env into `settings` but
# does not export to os.environ, and nothing calls load_dotenv(), so without this
# tracing silently stays off. config.py is imported before any model/graph init,
# so setting them here takes effect for every LangChain/LangGraph run.
os.environ["LANGSMITH_TRACING"] = str(settings.LANGSMITH_TRACING).lower()
os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
# Legacy aliases some LangChain versions still consult:
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGSMITH_TRACING).lower()
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY or settings.LANGSMITH_API_KEY