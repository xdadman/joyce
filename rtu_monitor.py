import asyncio

from advantech_adam import AdamDevice
from config import Config


class RtuMonitor:
    def __init__(self, adam_ip: str):
        self.adam = AdamDevice(adam_ip)
        self.connected = False


    async def read_requested_regulation(self):
        try:
            if not self.connected:
                await self.adam.connect()
                self.connected = True
        except Exception as e:
            print(f"Error while connecting to ADAM: {e}")
            return None

        try:
            inputs = await self.adam.read_digital_inputs(count=4)
            print(f"inputs: {inputs}")
            return inputs[0] + inputs[1] * 2 + inputs[2] * 4 + inputs[3] * 8
        except Exception as e:
            print(f"Error while getting inputs from ADAM: {e}")
            self.connected = False
            return None



async def main():
    cfg = Config()
    rtu_decoder = RtuMonitor(cfg.adam_ip)

    while True:
        regulation = await rtu_decoder.read_requested_regulation()
        print(f"regulation: {regulation}")
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
