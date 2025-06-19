import asyncio
import logging

import common
from modbus_meter import ModbusMeterClient


async def main():
    meter = ModbusMeterClient()
    await meter.modbus_meter_client_task()
    res = await self.client.read_holding_registers(9004, 2, slave=SLAVE)


if __name__ == '__main__':
    common.setup_logging(log_level=logging.INFO)
    asyncio.run(main())
