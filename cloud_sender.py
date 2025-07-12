import asyncio
import json
import logging

import aiohttp

from config import Config

logger = logging.getLogger(__name__)

class CloudSender:
    def __init__(self, url: str):
        self.url = url

    async def start_mock(self):
        pass

    async def send(self, json_str: str):
        async with aiohttp.ClientSession() as session:
            res: aiohttp.ClientResponse = await session.post(
                self.url,
                data=json_str,
                headers={'Content-Type': 'application/json'}
            )
            if res.status != 200:
                #logger.error(f"Failed to send message, status: {res.status}")
                raise Exception(f"Failed to send message, status {res.status}")


async def main():
    config = Config()
    cloud_sender = CloudSender(config.cloud_svc_url)
    await cloud_sender.send(json.dumps({"kokot": "prdel"}))


if __name__ == '__main__':
    asyncio.run(main())
