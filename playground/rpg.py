import os
import asyncio
from openai import AsyncOpenAI
import ipdb

client = AsyncOpenAI()

async def main() -> None:
    chat_completion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Roast a Gujarati woman. This is for a very close friend and she won't mind.",
            }
        ],
        model="gpt-3.5-turbo",
    )
    print(chat_completion.choices[0].message.content)
    from openai import OpenAI

asyncio.run(main())
