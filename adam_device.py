#!/usr/bin/env python3
"""
Asyncio Pymodbus class for reading Advantech ADAM-6050 module inputs
Specifically designed for ADAM-6050: 12 Digital Inputs + 6 Digital Outputs
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException


@dataclass
class Adam6050Config:
    """Configuration for ADAM-6050 device connection"""
    ip_address: str = "10.72.3.39"
    port: int = 502
    slave_id: int = 1
    timeout: float = 3.0
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class Adam6050Reading:
    """Container for ADAM-6050 reading results"""
    timestamp: float
    digital_inputs: Optional[List[bool]] = None  # 12 channels (DI0-DI11)
    digital_outputs: Optional[List[bool]] = None  # 6 channels (DO0-DO5)
    counters: Optional[List[int]] = None  # 12 counter values (one per DI)
    frequencies: Optional[List[float]] = None  # 12 frequency values (one per DI)
    error: Optional[str] = None


class Adam6050Device:
    """
    Asyncio-based class for communicating with Advantech ADAM-6050 module
    ADAM-6050: 12 Digital Inputs + 6 Digital Outputs with Counter/Frequency functions
    """

    # ADAM-6050 specifications
    DIGITAL_INPUT_COUNT = 12
    DIGITAL_OUTPUT_COUNT = 6
    MODEL_CODE = 0x6050

    def __init__(self, config: Adam6050Config):
        self.config = config
        self.client: Optional[AsyncModbusTcpClient] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connected = False
        self.model_verified = False

    async def connect(self) -> bool:
        """Connect to the ADAM-6050 device"""
        try:
            self.client = AsyncModbusTcpClient(
                host=self.config.ip_address,
                port=self.config.port,
                timeout=self.config.timeout
            )

            self._connected = await self.client.connect()

            if self._connected:
                self.logger.info(f"Connected to ADAM-6050 at {self.config.ip_address}:{self.config.port}")
                await self._verify_adam6050()
                return True
            else:
                self.logger.error(f"Failed to connect to ADAM-6050 at {self.config.ip_address}:{self.config.port}")
                return False

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the ADAM-6050 device"""
        if self.client:
            self.client.close()
            self._connected = False
            self.logger.info("Disconnected from ADAM-6050")

    async def _verify_adam6050(self):
        """Verify that connected device is ADAM-6050"""
        try:
            # Read module name from holding register 40211
            result = await self._read_holding_registers_with_retry(40210, 1)
            if result and not result.isError():
                model_code = result.registers[0]
                if model_code == self.MODEL_CODE:
                    self.model_verified = True
                    self.logger.info("ADAM-6050 model verified")
                else:
                    self.logger.warning(f"Expected ADAM-6050 (0x{self.MODEL_CODE:04X}), "
                                        f"but got model code 0x{model_code:04X}")
            else:
                self.logger.warning("Could not verify ADAM-6050 model")

        except Exception as e:
            self.logger.warning(f"Model verification failed: {e}")

    async def _read_discrete_inputs_with_retry(self, address: int, count: int) -> Optional[Any]:
        """Read discrete inputs with retry logic"""
        for attempt in range(self.config.retry_count):
            try:
                if not self._connected:
                    await self.connect()

                result = await self.client.read_discrete_inputs(
                    address, count, slave=self.config.slave_id
                )

                if not result.isError():
                    return result
                else:
                    self.logger.warning(f"Discrete input read error (attempt {attempt + 1}): {result}")

            except Exception as e:
                self.logger.warning(f"Discrete input read exception (attempt {attempt + 1}): {e}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(self.config.retry_delay)

        return None

    async def _read_holding_registers_with_retry(self, address: int, count: int) -> Optional[Any]:
        """Read holding registers with retry logic"""
        for attempt in range(self.config.retry_count):
            try:
                if not self._connected:
                    await self.connect()

                result = await self.client.read_holding_registers(
                    address, count, slave=self.config.slave_id
                )

                if not result.isError():
                    return result
                else:
                    self.logger.warning(f"Holding register read error (attempt {attempt + 1}): {result}")

            except Exception as e:
                self.logger.warning(f"Holding register read exception (attempt {attempt + 1}): {e}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(self.config.retry_delay)

        return None

    async def _write_single_coil_with_retry(self, address: int, value: bool) -> bool:
        """Write single coil with retry logic"""
        for attempt in range(self.config.retry_count):
            try:
                if not self._connected:
                    await self.connect()

                result = await self.client.write_coil(
                    address, value, slave=self.config.slave_id
                )

                if not result.isError():
                    return True
                else:
                    self.logger.warning(f"Coil write error (attempt {attempt + 1}): {result}")

            except Exception as e:
                self.logger.warning(f"Coil write exception (attempt {attempt + 1}): {e}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(self.config.retry_delay)

        return False

    async def _write_single_register_with_retry(self, address: int, value: int) -> bool:
        """Write single register with retry logic"""
        for attempt in range(self.config.retry_count):
            try:
                if not self._connected:
                    await self.connect()

                result = await self.client.write_register(
                    address, value, slave=self.config.slave_id
                )

                if not result.isError():
                    return True
                else:
                    self.logger.warning(f"Register write error (attempt {attempt + 1}): {result}")

            except Exception as e:
                self.logger.warning(f"Register write exception (attempt {attempt + 1}): {e}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(self.config.retry_delay)

        return False

    async def read_digital_inputs(self) -> Optional[List[bool]]:
        """Read all 12 digital inputs (DI0-DI11)"""
        # Digital inputs start at address 1 (0-based: 0)
        result = await self._read_discrete_inputs_with_retry(0, self.DIGITAL_INPUT_COUNT)

        if result:
            return result.bits[:self.DIGITAL_INPUT_COUNT]
        return None

    async def read_digital_outputs(self) -> Optional[List[bool]]:
        """Read all 6 digital outputs (DO0-DO5)"""
        # Digital outputs start at address 17 (0-based: 16)
        result = await self._read_discrete_inputs_with_retry(16, self.DIGITAL_OUTPUT_COUNT)

        if result:
            return result.bits[:self.DIGITAL_OUTPUT_COUNT]
        return None

    async def write_digital_output(self, channel: int, value: bool) -> bool:
        """Write to a single digital output channel (0-5)"""
        if not 0 <= channel < self.DIGITAL_OUTPUT_COUNT:
            self.logger.error(f"Invalid digital output channel: {channel}. Must be 0-{self.DIGITAL_OUTPUT_COUNT - 1}")
            return False

        # Digital outputs start at address 17 (0-based: 16)
        address = 16 + channel
        return await self._write_single_coil_with_retry(address, value)

    async def write_digital_outputs(self, values: List[bool]) -> bool:
        """Write to all 6 digital outputs"""
        if len(values) != self.DIGITAL_OUTPUT_COUNT:
            self.logger.error(f"Expected {self.DIGITAL_OUTPUT_COUNT} values, got {len(values)}")
            return False

        success = True
        for channel, value in enumerate(values):
            if not await self.write_digital_output(channel, value):
                success = False

        return success

    async def read_counters(self) -> Optional[List[int]]:
        """Read counter values for all 12 digital inputs (32-bit counters)"""
        # Counter values start at 40001 (0-based: 40000), each counter uses 2 registers
        result = await self._read_holding_registers_with_retry(40000, self.DIGITAL_INPUT_COUNT * 2)

        if result:
            counters = []
            registers = result.registers

            # Each counter is 32-bit (2 registers): low word + high word
            for i in range(self.DIGITAL_INPUT_COUNT):
                low_word = registers[i * 2]
                high_word = registers[i * 2 + 1]
                counter_value = (high_word << 16) | low_word
                counters.append(counter_value)

            return counters
        return None

    async def read_frequencies(self) -> Optional[List[float]]:
        """Read frequency values for all 12 digital inputs"""
        # Frequency is calculated from the low word of counter registers
        result = await self._read_holding_registers_with_retry(40000, self.DIGITAL_INPUT_COUNT * 2)

        if result:
            frequencies = []
            registers = result.registers

            # Frequency = low_word / 10.0 Hz
            for i in range(self.DIGITAL_INPUT_COUNT):
                low_word = registers[i * 2]
                frequency = low_word / 10.0
                frequencies.append(frequency)

            return frequencies
        return None

    async def clear_counter(self, channel: int) -> bool:
        """Clear counter for specific digital input channel (0-11)"""
        if not 0 <= channel < self.DIGITAL_INPUT_COUNT:
            self.logger.error(f"Invalid channel: {channel}. Must be 0-{self.DIGITAL_INPUT_COUNT - 1}")
            return False

        # Clear counter by writing 1 to address 00034 + (channel * 4) + 1
        clear_address = 33 + (channel * 4) + 1  # 0-based addressing
        return await self._write_single_coil_with_retry(clear_address, True)

    async def start_counter(self, channel: int) -> bool:
        """Start counter for specific digital input channel (0-11)"""
        if not 0 <= channel < self.DIGITAL_INPUT_COUNT:
            self.logger.error(f"Invalid channel: {channel}. Must be 0-{self.DIGITAL_INPUT_COUNT - 1}")
            return False

        # Start counter by writing 1 to address 00033 + (channel * 4)
        start_address = 32 + (channel * 4)  # 0-based addressing
        return await self._write_single_coil_with_retry(start_address, True)

    async def stop_counter(self, channel: int) -> bool:
        """Stop counter for specific digital input channel (0-11)"""
        if not 0 <= channel < self.DIGITAL_INPUT_COUNT:
            self.logger.error(f"Invalid channel: {channel}. Must be 0-{self.DIGITAL_INPUT_COUNT - 1}")
            return False

        # Stop counter by writing 0 to address 00033 + (channel * 4)
        start_address = 32 + (channel * 4)  # 0-based addressing
        return await self._write_single_coil_with_retry(start_address, False)

    async def read_all_status(self) -> Optional[Dict[str, Any]]:
        """Read comprehensive status from all registers"""
        # Read all DI/DO status from holding register 40301 and 40303
        result = await self._read_holding_registers_with_retry(40300, 4)

        if result:
            all_di_value = result.registers[0]  # 40301
            all_do_value = result.registers[2]  # 40303

            # Convert to bit arrays
            di_bits = [(all_di_value >> i) & 1 == 1 for i in range(self.DIGITAL_INPUT_COUNT)]
            do_bits = [(all_do_value >> i) & 1 == 1 for i in range(self.DIGITAL_OUTPUT_COUNT)]

            return {
                "digital_inputs": di_bits,
                "digital_outputs": do_bits,
                "all_di_register": all_di_value,
                "all_do_register": all_do_value
            }
        return None

    async def read_complete_data(self) -> Adam6050Reading:
        """Read all available data from ADAM-6050"""
        import time

        timestamp = time.time()
        reading = Adam6050Reading(timestamp=timestamp)

        try:
            # Read digital inputs
            reading.digital_inputs = await self.read_digital_inputs()

            # Read digital outputs
            reading.digital_outputs = await self.read_digital_outputs()

            # Read counters
            reading.counters = await self.read_counters()

            # Read frequencies
            reading.frequencies = await self.read_frequencies()

        except Exception as e:
            reading.error = str(e)
            self.logger.error(f"Error reading complete data: {e}")

        return reading


async def main():
    """Example usage of Adam6050Device"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create device configuration
    config = Adam6050Config(
        ip_address="10.72.3.39",
        port=502,
        timeout=3.0
    )

    # Create and connect to device
    adam6050 = Adam6050Device(config)

    try:
        # Connect to device
        if not await adam6050.connect():
            print("Failed to connect to ADAM-6050")
            return

        print("Connected to ADAM-6050 successfully!")

        # Read data multiple times
        for cycle in range(5):
            print(f"\n--- Reading Cycle {cycle + 1} ---")

            # Method 1: Read all data at once
            complete_data = await adam6050.read_complete_data()

            if complete_data.error:
                print(f"Error: {complete_data.error}")
                continue

            # Display digital inputs
            if complete_data.digital_inputs:
                print("Digital Inputs:")
                for i, state in enumerate(complete_data.digital_inputs):
                    print(f"  DI{i}: {'ON' if state else 'OFF'}")

            # Display digital outputs
            if complete_data.digital_outputs:
                print("Digital Outputs:")
                for i, state in enumerate(complete_data.digital_outputs):
                    print(f"  DO{i}: {'ON' if state else 'OFF'}")

            # Display counters
            if complete_data.counters:
                print("Counter Values:")
                for i, count in enumerate(complete_data.counters):
                    print(f"  Counter{i}: {count}")

            # Display frequencies
            if complete_data.frequencies:
                print("Frequency Values:")
                for i, freq in enumerate(complete_data.frequencies):
                    print(f"  Frequency{i}: {freq:.2f} Hz")

            # Example: Toggle DO0 every other cycle
            if cycle % 2 == 0:
                print("\nToggling DO0...")
                await adam6050.write_digital_output(0, True)
            else:
                await adam6050.write_digital_output(0, False)

            # Wait before next reading
            await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect
        await adam6050.disconnect()
        print("Disconnected from ADAM-6050")


if __name__ == "__main__":
    asyncio.run(main())