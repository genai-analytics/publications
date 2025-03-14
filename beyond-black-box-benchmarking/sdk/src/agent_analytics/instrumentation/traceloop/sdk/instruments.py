from enum import Enum


class Instruments(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    PINECONE = "pinecone"
    CHROMA = "chroma"
    GOOGLE_GENERATIVEAI = "google_generativeai"
    LANGCHAIN = "langchain"
    # Add Langgraph
    LANGGRAPH = "langgraph"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    LLAMA_INDEX = "llama_index"
    MILVUS = "milvus"
    TRANSFORMERS = "transformers"
    TOGETHER = "together"
    REDIS = "redis"
    REQUESTS = "requests"
    URLLIB3 = "urllib3"
    PYMYSQL = "pymysql"
    BEDROCK = "bedrock"
    REPLICATE = "replicate"
    VERTEXAI = "vertexai"
    WATSONX = "watsonx"
    WEAVIATE = "weaviate"
    ALEPHALPHA = "alephalpha"
    MARQO = "marqo"
    LANCEDB = "lancedb"
    SAGEMAKER = "sagemaker"
    FASTAPI = "fastapi"
