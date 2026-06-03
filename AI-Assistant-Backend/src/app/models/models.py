from langchain_openai import ChatOpenAI
from langchain_deepseek import  ChatDeepSeek
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings


#--------------------- Models wihout tools -------------------------

# Deepseek Flash — cheap default synthesizer for the "general" category.
deepseek_flash_model = ChatDeepSeek(
    model="deepseek-v4-flash",
    temperature=0,
    max_tokens=8000,
    api_key=settings.DEEPSEEK_API_KEY,
    reasoning_effort="low",
    )

# Deepseek Pro — strong reasoner; primary synthesizer for math/code categories.
deepseek_pro_model = ChatDeepSeek(
    model="deepseek-v4-pro",
    temperature=0,
    max_tokens=8000,
    api_key=settings.DEEPSEEK_API_KEY,
    reasoning_effort="low",
    )

# Groq GPT OSS 20B — used by the Tavily web-search node (mcp/tavily_search.py).
groq_gpt_model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=4000,
    api_key=settings.GROQ_API_KEY
)

# OpenAI GPT-5 Nano — summarizer for the context-management node.
gpt_5_nano_model = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0,
    reasoning_effort="low",
    max_tokens=500,
    reasoning_effort="low",
    api_key=settings.OPENAI_API_KEY
)

# OpenAI GPT-5 Mini — reliable structured output; query-analyzer primary +
# vision-synthesizer fallback.
gpt_5_mini_model = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0,
    reasoning_effort="low",
    api_key=settings.OPENAI_API_KEY
)

# OpenAI GPT-5 — strong general model; provider-error fallback for math/code.
gpt_5_model = ChatOpenAI(
    model="gpt-5",
    temperature=0,
    reasoning_effort="low",
    api_key=settings.OPENAI_API_KEY
)

# Gemini 2.5 Flash — vision-capable; image-synthesizer primary + query-analyzer
# structured-output fallback.
gemini_flash_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=settings.GEMINI_API_KEY,
    temperature=0,
)
