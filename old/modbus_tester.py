import asyncio

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

SERIAL_PORT = "SERIAL_PORT"
SERIAL_BAUDRATE = "SERIAL_BAUDRATE"
SERIAL_STOPBITS = "SERIAL_STOPBITS"
SERIAL_PARITY = "SERIAL_PARITY"

SLAVE = 100

class Tester:
    def __init__(self):
        self.cfg = {
            SERIAL_PORT: "/dev/ttyUSB0",
            SERIAL_BAUDRATE: 9600,
            SERIAL_STOPBITS: 1,
            SERIAL_PARITY: "E",
        }

    async def run(self):
        self.client = AsyncModbusSerialClient(
            port=self.cfg[SERIAL_PORT],  # serial port
            # Common optional paramers:
            #    framer=ModbusRtuFramer,
            #    timeout=10,
            #    retries=3,
            #    retry_on_empty=False,
            #    close_comm_on_error=False,.
            #    strict=True,
            # Serial setup parameters
            baudrate=self.cfg[SERIAL_BAUDRATE],
            bytesize=8,
            parity=self.cfg[SERIAL_PARITY],
            stopbits=self.cfg[SERIAL_STOPBITS],
            #    handle_local_echo=False,
        )
        await self.client.connect()
        result = await self.client.read_holding_registers(0, 32, slave=SLAVE)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        u1 = decoder.decode_32bit_float()
        print(f"U1: {u1}")


async def main():
    test = Tester()
    await test.run()


if __name__ == '__main__':
    asyncio.run(main())
