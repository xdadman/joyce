import asyncio

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

SERIAL_PORT = "SERIAL_PORT"
SERIAL_BAUDRATE = "SERIAL_BAUDRATE"
SERIAL_STOPBITS = "SERIAL_STOPBITS"
SERIAL_PARITY = "SERIAL_PARITY"

SLAVE = 247

class Tester:
    def __init__(self):
        self.cfg = {
            SERIAL_PORT: "/dev/ttyUSB0",
            SERIAL_BAUDRATE: 9600,
            SERIAL_STOPBITS: 1,
            SERIAL_PARITY: "N",
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
        result = await self.client.read_holding_registers(32016, 1, slave=SLAVE)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        pv1 = decoder.decode_16bit_uint()
        print(f"PV1: {pv1}")


async def main():
    test = Tester()
    await test.run()


if __name__ == '__main__':
    asyncio.run(main())
