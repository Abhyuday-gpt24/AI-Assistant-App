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
    NAMESPACE_METADATA: str
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