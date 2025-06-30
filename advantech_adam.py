#!/usr/bin/env python3
"""
Pymodbus example for reading Advantech ADAM-6000 module inputs
Compatible with ADAM-6050, ADAM-6052, ADAM-6060, ADAM-6066, etc.
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import time

# Configuration
ADAM_IP = "10.72.3.39"
ADAM_PORT = 502
SLAVE_ID = 1  # Default slave ID for ADAM modules


def read_digital_inputs(client, start_address=0x01, count=8):
    """
    Read digital inputs from ADAM module
    ADAM-6050/6052: Typically addresses 0x01-0x08 for 8 digital inputs
    ADAM-6060/6066: Typically addresses 0x01-0x06 for 6 digital inputs
    """
    try:
        result = client.read_discrete_inputs(start_address, count, slave=SLAVE_ID)
        if result.isError():
            print(f"Error reading digital inputs: {result}")
            return None
        return result.bits[:count]
    except ModbusException as e:
        print(f"Modbus exception reading digital inputs: {e}")
        return None


def read_analog_inputs(client, start_address=0x01, count=4):
    """
    Read analog inputs from ADAM module
    ADAM-6017/6018: Typically 8 analog input channels
    Values are usually in engineering units or raw ADC values
    """
    try:
        result = client.read_input_registers(start_address, count, slave=SLAVE_ID)
        if result.isError():
            print(f"Error reading analog inputs: {result}")
            return None
        return result.registers
    except ModbusException as e:
        print(f"Modbus exception reading analog inputs: {e}")
        return None


def read_holding_registers(client, start_address=0x01, count=4):
    """
    Read holding registers (configuration and status)
    """
    try:
        result = client.read_holding_registers(start_address, count, slave=SLAVE_ID)
        if result.isError():
            print(f"Error reading holding registers: {result}")
            return None
        return result.registers
    except ModbusException as e:
        print(f"Modbus exception reading holding registers: {e}")
        return None


def main():
    # Create Modbus TCP client
    client = ModbusTcpClient(host=ADAM_IP, port=ADAM_PORT, timeout=3)

    try:
        # Connect to the ADAM module
        print(f"Connecting to ADAM module at {ADAM_IP}:{ADAM_PORT}")
        connection = client.connect()

        if not connection:
            print("Failed to connect to ADAM module")
            return

        print("Connected successfully!")

        # Read data in a loop
        for i in range(5):  # Read 5 times as example
            print(f"\n--- Reading cycle {i + 1} ---")

            # Read digital inputs (adjust count based on your ADAM model)
            digital_inputs = read_digital_inputs(client, start_address=0x01, count=8)
            if digital_inputs is not None:
                print("Digital Inputs:")
                for j, state in enumerate(digital_inputs):
                    print(f"  DI{j + 1}: {'ON' if state else 'OFF'}")


            # Read some holding registers (module status/config)
            holding_regs = read_holding_registers(client, start_address=0x01, count=2)
            if holding_regs is not None:
                print("Holding Registers:")
                for j, value in enumerate(holding_regs):
                    print(f"  HR{j + 1}: {value}")

            time.sleep(2)  # Wait 2 seconds between readings

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the connection
        client.close()
        print("Connection closed")


def read_module_info(client):
    """
    Read module identification information
    """
    try:
        # Read module name (typically at holding register 0x0000)
        result = client.read_holding_registers(0x0000, 4, slave=SLAVE_ID)
        if not result.isError():
            print("Module Info:")
            print(f"  Registers 0x0000-0x0003: {result.registers}")

        # Read firmware version (location varies by model)
        result = client.read_holding_registers(0x0004, 2, slave=SLAVE_ID)
        if not result.isError():
            print(f"  Firmware info: {result.registers}")

    except ModbusException as e:
        print(f"Error reading module info: {e}")


if __name__ == "__main__":
    main()