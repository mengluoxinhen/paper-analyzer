import asyncio
from app.database import async_session
from app.papers.service import _get_llm_config, _get_client

async def test():
    async with async_session() as db:
        cfg = await _get_llm_config(db)
        print("Config:", cfg)
        client, cfg2 = await _get_client(db)
        print("Client created OK")
        
        # Try a simple completion
        try:
            stream = await client.chat.completions.create(
                model=cfg["model"],
                messages=[{"role": "user", "content": "Say hello in one word"}],
                max_tokens=10,
                stream=True,
            )
            async for chunk in stream:
                d = chunk.choices[0].delta
                if d.content:
                    print(d.content, end="", flush=True)
            print()
            print("LLM call succeeded!")
        except Exception as e:
            print(f"LLM error: {e}")

asyncio.run(test())
