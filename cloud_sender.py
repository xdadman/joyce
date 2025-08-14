import asyncio
import json
import logging
import threading
import time

import aiohttp

from config import Config
import flask_server

logger = logging.getLogger(__name__)

class CloudSender:
    def __init__(self, url: str):
        self.url = url

    async def start_mock(self):
        def run_flask():
            flask_server.main()
        
        thread = threading.Thread(target=run_flask, daemon=True)
        thread.start()
        await asyncio.sleep(1)  # Give Flask time to start

    async def send(self, json_str: str):
        logger.info("Sending message to cloud service...")
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            res: aiohttp.ClientResponse = await session.post(
                self.url,
                data=json_str,
                headers={'Content-Type': 'application/json'}
            )
            if res.status != 200:
                #logger.error(f"Failed to send message, status: {res.status}")
                raise Exception(f"Failed to send message, status {res.status}")
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Successfully sent message to cloud service {execution_time:.2f} sec")


async def main():
    config = Config()
    cloud_sender = CloudSender(config.cloud_svc_url)
    await cloud_sender.start_mock()
    await cloud_sender.send(json.dumps({"kokot": "prdel"}))


if __name__ == '__main__':
    asyncio.run(main())
