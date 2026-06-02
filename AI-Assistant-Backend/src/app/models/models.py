from langchain_openai import ChatOpenAI
from langchain_deepseek import  ChatDeepSeek
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings


#--------------------- Models wihout tools -------------------------

# Deepseek Flash — default synthesizer (general/chit-chat) + query analyzer
deepseek_flash_model = ChatDeepSeek(
    model="deepseek-v4-flash",
    temperature=0,
    max_tokens=8000,
    api_key=settings.DEEPSEEK_API_KEY,
    reasoning_effort="low",
    )

# Deepseek Pro — strong reasoner; synthesizer tier for math/code categories
deepseek_pro_model = ChatDeepSeek(
    model="deepseek-v4-pro",
    temperature=0,
    max_tokens=8000,
    api_key=settings.DEEPSEEK_API_KEY,
    reasoning_effort="medium",
    )

# Groq GPT OSS 20B
groq_gpt_model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=4000,
    api_key=settings.GROQ_API_KEY
)

# OpenAI GPT 5 Nano
gpt_5_nano_model = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0,
    reasoning_effort="low",
    max_tokens=500,
    api_key=settings.OPENAI_API_KEY
)

gpt_5_mini_model = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0,
    reasoning_effort="medium",
    api_key=settings.OPENAI_API_KEY
)

gpt_54_mini_model = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0,
    reasoning_effort="medium",
    api_key=settings.OPENAI_API_KEY
)

gpt_54_nano_model = ChatOpenAI(
    model="gpt-5.4-nano",
    temperature=0,
    reasoning_effort="medium",
    api_key=settings.OPENAI_API_KEY
)

gpt_54_mini_model = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0,
    reasoning_effort="medium",
    api_key=settings.OPENAI_API_KEY
)

gpt_54_model = ChatOpenAI(
    model="gpt-5.4",
    temperature=0,
    reasoning_effort="medium",
    api_key=settings.OPENAI_API_KEY
)

gpt_55_model = ChatOpenAI(
    model="gpt-5.5",
    temperature=0,
    reasoning_effort="medium",
    api_key=settings.OPENAI_API_KEY
)

# Gemini Flash — vision-capable; fallback for the image synthesizer path
gemini_flash_model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    api_key=settings.GEMINI_API_KEY,
    temperature=0,
)







