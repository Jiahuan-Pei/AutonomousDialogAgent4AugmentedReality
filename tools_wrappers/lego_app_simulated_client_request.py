import asyncio
import os
from typing import Dict

import aiohttp
from pydantic import BaseModel, ValidationError

from dotenv import load_dotenv, find_dotenv
# load environment variables in .env file
load_dotenv(find_dotenv())
import os


class Response(BaseModel):
    result: str
    error: str
    stdout: str


class HumanPrompt(BaseModel):
    prompt: str


async def hitl_client(url: str, name: str, query: str, envs: Dict = {}):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f'{url}/{name}') as ws:
            print(f'Connected to {url}/{name}.')

            await ws.send_json(
                {
                    "query": query,
                    "envs": envs if envs else {},
                }
            )

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == 'q':     # close cmd
                        await ws.close()
                        break
                    else:
                        try:
                            response = Response.parse_raw(msg.data)
                            print(response.stdout, end='')
                            print(response.result, end='')

                        except ValidationError:
                            try:
                                prompt = HumanPrompt.parse_raw(msg.data)
                                answer = input(prompt.prompt + '\n')
                                await ws.send_str(answer)
                            except ValidationError:
                                print(f'Unknown message: {msg.data}')

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print('ws connection closed with exception %s' % ws.exception())
                else:
                    print(msg)


def test_one_time_api():
    asyncio.run(
        hitl_client(
            # url='wss://langchain-9468f429d4-websocket.wolf.jina.ai',
            url='ws://localhost:8080',  # Private endpoint
            name='citl',
            query='Hi can you be my personal assistant to teach me how to assembly a LEGO car? Let\'s start.',
            envs={
                'OPENAI_API_KEY': os.environ['OPENAI_API_KEY']
            },
        )
    )


if __name__ == "__main__":
    test_one_time_api()


