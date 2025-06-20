import asyncio

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from registers_goodwe_ht import GoodweHTRegs, RegName

SERIAL_PORT = "SERIAL_PORT"
SERIAL_BAUDRATE = "SERIAL_BAUDRATE"
SERIAL_STOPBITS = "SERIAL_STOPBITS"
SERIAL_PARITY = "SERIAL_PARITY"

SLAVE = 247

class Tester:
    def __init__(self):
        self.cfg = {
            #SERIAL_PORT: "/dev/ttyUSB0",
            SERIAL_PORT: "/tmp/ttyVirtual",
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
        result0 = await self.client.read_holding_registers(32002, 1, slave=SLAVE)
        result1 = await self.client.read_holding_registers(32016, 4, slave=SLAVE)
        regs = GoodweHTRegs()

        regs.decode(result0.registers, regs.get(RegName.OPER_STATUS).address, regs.get(RegName.OPER_STATUS).address)
        regs.decode(result1.registers, regs.get(RegName.PV1_U).address, regs.get(RegName.PV2_C).address)

        status = regs.get_value(RegName.OPER_STATUS)
        print(status)

        pv1_u = regs.get_value(RegName.PV1_U)
        pv1_c = regs.get_value(RegName.PV1_C)

        print(f"PV1: {pv1_u} {pv1_c}")


async def main():
    test = Tester()
    await test.run()


if __name__ == '__main__':
    asyncio.run(main())
