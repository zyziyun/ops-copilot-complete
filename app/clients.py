from openai import AsyncOpenAI

from app.config import settings

aclient = AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    resp = await aclient.embeddings.create(model=settings.embed_model, input=texts)
    return [row.embedding for row in resp.data]
