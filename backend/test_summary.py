import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", "http://localhost:8000/api/papers/4/summarize") as resp:
            print(f"Status: {resp.status_code}")
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        print("\n[DONE]")
                        break
                    if data.startswith("[ERROR]"):
                        print(f"\n!!! {data}")
                        break
                    print(data[:80], end="", flush=True)

asyncio.run(test())
