#!/usr/bin/env python3
"""
Pymodbus example for reading Advantech ADAM-6000 module inputs
Compatible with ADAM-6050
"""

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
import asyncio
import logging

log = logging.getLogger(__name__)

class AdamDevice:
    def __init__(self, ip, port=502, slave_id=1, timeout=3):
        self.ip = ip
        self.port = port
        self.slave_id = slave_id
        self.timeout = timeout
        self.client = None

    async def connect(self):
        """Connect to the ADAM module"""
        self.client = AsyncModbusTcpClient(host=self.ip, port=self.port, timeout=self.timeout)
        print(f"Connecting to ADAM module at {self.ip}:{self.port}")
        connection = await self.client.connect()
        
        if not connection:
            print("Failed to connect to ADAM module")
            return False
        
        print("Connected successfully!")
        return True

    async def disconnect(self):
        """Disconnect from the ADAM module"""
        if self.client:
            await self.client.close()
            print("Connection closed")

    async def read_digital_inputs(self, start_address=0, count=8):
        """
        Read digital inputs from ADAM module
        ADAM-6050/6052: Typically addresses 0x01-0x08 for 8 digital inputs
        ADAM-6060/6066: Typically addresses 0x01-0x06 for 6 digital inputs
        """
        try:
            result = await self.client.read_discrete_inputs(start_address, count, slave=self.slave_id)
            if result.isError():
                print(f"Error reading digital inputs: {result}")
                return None
            return result.bits[:count]
        except ModbusException as e:
            print(f"Modbus exception reading digital inputs: {e}")
            return None

    async def read_analog_inputs(self, start_address=0x01, count=4):
        """
        Read analog inputs from ADAM module
        ADAM-6017/6018: Typically 8 analog input channels
        Values are usually in engineering units or raw ADC values
        """
        try:
            result = await self.client.read_input_registers(start_address, count, slave=self.slave_id)
            if result.isError():
                print(f"Error reading analog inputs: {result}")
                return None
            return result.registers
        except ModbusException as e:
            print(f"Modbus exception reading analog inputs: {e}")
            return None

    async def read_holding_registers(self, start_address=0x01, count=4):
        """
        Read holding registers (configuration and status)
        """
        try:
            result = await self.client.read_holding_registers(start_address, count, slave=self.slave_id)
            if result.isError():
                print(f"Error reading holding registers: {result}")
                return None
            return result.registers
        except ModbusException as e:
            print(f"Modbus exception reading holding registers: {e}")
            return None

    async def write_holding_registers(self, start_address, values):
        """
        Write holding registers (configuration and control)
        Args:
            start_address: Starting register address
            values: List of values to write or single value
        """
        try:
            if isinstance(values, (list, tuple)):
                result = await self.client.write_registers(start_address, values, slave=self.slave_id)
            else:
                result = await self.client.write_register(start_address, values, slave=self.slave_id)
            
            if result.isError():
                print(f"Error writing holding registers: {result}")
                return False
            return True
        except ModbusException as e:
            print(f"Modbus exception writing holding registers: {e}")
            return False

    async def write_digital_outputs(self, start_address, values):
        """
        Write digital outputs (coils) to ADAM module
        Args:
            start_address: Starting coil address
            values: List of boolean values or single boolean value
        """
        try:
            if isinstance(values, (list, tuple)):
                result = await self.client.write_coils(start_address, values, slave=self.slave_id)
            else:
                result = await self.client.write_coil(start_address, values, slave=self.slave_id)
            
            if result.isError():
                print(f"Error writing digital outputs: {result}")
                return False
            return True
        except ModbusException as e:
            print(f"Modbus exception writing digital outputs: {e}")
            return False

    async def read_module_info(self):
        """
        Read module identification information
        """
        try:
            # Read module name (typically at holding register 0x0000)
            result = await self.client.read_holding_registers(0x0000, 4, slave=self.slave_id)
            if not result.isError():
                print("Module Info:")
                print(f"  Registers 0x0000-0x0003: {result.registers}")

            # Read firmware version (location varies by model)
            result = await self.client.read_holding_registers(0x0004, 2, slave=self.slave_id)
            if not result.isError():
                print(f"  Firmware info: {result.registers}")

        except ModbusException as e:
            print(f"Error reading module info: {e}")

    async def read_cycle(self, digital_count=8, holding_count=2):
        """
        Perform a complete read cycle of digital inputs and holding registers
        """
        # Read digital inputs
        digital_inputs = await self.read_digital_inputs(start_address=0, count=digital_count)
        if digital_inputs is not None:
            print("Digital Inputs:")
            for j, state in enumerate(digital_inputs):
                print(f"  DI{j}: {'ON' if state else 'OFF'}")

        # # Read holding registers
        # holding_regs = await self.read_holding_registers(start_address=0x01, count=holding_count)
        # if holding_regs is not None:
        #     print("Holding Registers:")
        #     for j, value in enumerate(holding_regs):
        #         print(f"  HR{j + 1}: {value}")


async def main():
    # Create ADAM device instance
    adam = AdamDevice("10.72.3.39")

    try:
        # Connect to the ADAM module
        if not await adam.connect():
            return

        await adam.write_digital_outputs(start_address=16, values=[1, 0, 0, 1])
        #await adam.write_digital_outputs(start_address=16, values=[1, 1, 1, 1])
        #await adam.write_digital_outputs(start_address=16, values=[0, 0, 0, 0])
        #await adam.write_holding_registers(start_address=17, values=[0])

        # while True:
        #     digital_inputs = await adam.read_digital_inputs(start_address=16, count=7)
        #     print(f"ous {digital_inputs}")
        #     await asyncio.sleep(1)

        # Read data in a loop
        for i in range(50):  # Read 50 times as example
            print(f"\n--- Reading cycle {i + 1} ---")
            await adam.read_cycle()
            await asyncio.sleep(2)  # Wait 2 seconds between readings

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the connection
        await adam.disconnect()


if __name__ == "__main__":
    asyncio.run(main())