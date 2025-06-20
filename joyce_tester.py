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
        self.regs = GoodweHTRegs()

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
        regs = self.regs

        result0 = await self.client.read_holding_registers(32002, 1, slave=SLAVE)
        result1 = await self.client.read_holding_registers(32016, self.addr_diff(RegName.PV1_U, RegName.INTERNAL_TEMPERATURE), slave=SLAVE)
        result2 = await self.client.read_holding_registers(32106, self.addr_diff(RegName.CUMULATIVE_POWER_GENERATION, RegName.POWER_GENERATION_YEAR), slave=SLAVE)
        #result3 = await self.client.read_holding_registers(32180, self.addr_diff(RegName.ACTIVE_POWER_CALCULATION, RegName.ACTIVE_POWER_CALCULATION), slave=SLAVE)


        regs.decode(result0.registers, regs.get(RegName.OPER_STATUS).address, regs.get(RegName.OPER_STATUS).address)
        regs.decode(result1.registers, regs.get(RegName.PV1_U).address, regs.get(RegName.INTERNAL_TEMPERATURE).address)
        regs.decode(result2.registers, regs.get(RegName.CUMULATIVE_POWER_GENERATION).address, regs.get(RegName.POWER_GENERATION_YEAR).address)
        #regs.decode(result3.registers, regs.get(RegName.ACTIVE_POWER_CALCULATION).address, regs.get(RegName.ACTIVE_POWER_CALCULATION).address)

        status = regs.get_value(RegName.OPER_STATUS)
        print(status)

        for i in range(1, 25):
            pv_u_name = getattr(RegName, f"PV{i}_U")
            pv_c_name = getattr(RegName, f"PV{i}_C")
            
            pv_u = regs.get_value(pv_u_name)
            pv_c = regs.get_value(pv_c_name)
            
            print(f"PV{i}: {pv_u:0.1f}V {pv_c:0.2f}A")

        print("\n--- Additional Registers ---")
        input_power = regs.get_value(RegName.INPUT_POWER)
        print(f"Input Power: {input_power:0.2f} kW")
        
        grid_ab_voltage = regs.get_value(RegName.GRID_AB_VOLTAGE)
        grid_bc_voltage = regs.get_value(RegName.GRID_BC_VOLTAGE)
        grid_ca_voltage = regs.get_value(RegName.GRID_CA_VOLTAGE)
        print(f"Grid Line Voltages - AB: {grid_ab_voltage:0.1f}V, BC: {grid_bc_voltage:0.1f}V, CA: {grid_ca_voltage:0.1f}V")
        
        grid_a_voltage = regs.get_value(RegName.GRID_A_VOLTAGE)
        grid_b_voltage = regs.get_value(RegName.GRID_B_VOLTAGE)
        grid_c_voltage = regs.get_value(RegName.GRID_C_VOLTAGE)
        print(f"Grid Phase Voltages - A: {grid_a_voltage:0.1f}V, B: {grid_b_voltage:0.1f}V, C: {grid_c_voltage:0.1f}V")
        
        grid_a_current = regs.get_value(RegName.GRID_A_CURRENT)
        grid_b_current = regs.get_value(RegName.GRID_B_CURRENT)
        grid_c_current = regs.get_value(RegName.GRID_C_CURRENT)
        print(f"Grid Currents - A: {grid_a_current:0.3f}A, B: {grid_b_current:0.3f}A, C: {grid_c_current:0.3f}A")
        
        peak_active_power_day = regs.get_value(RegName.PEAK_ACTIVE_POWER_DAY)
        active_power = regs.get_value(RegName.ACTIVE_POWER)
        reactive_power = regs.get_value(RegName.REACTIVE_POWER)
        power_factor = regs.get_value(RegName.POWER_FACTOR)
        print(f"Peak Active Power (Day): {peak_active_power_day:0.2f} kW")
        print(f"Active Power: {active_power:0.2f} kW")
        print(f"Reactive Power: {reactive_power:0.2f} kvar")
        print(f"Power Factor: {power_factor:0.3f}")
        
        print("\n--- Power Quality & Efficiency ---")
        grid_frequency = regs.get_value(RegName.GRID_FREQUENCY)
        inverter_efficiency = regs.get_value(RegName.INVERTER_EFFICIENCY)
        internal_temperature = regs.get_value(RegName.INTERNAL_TEMPERATURE)
        print(f"Grid Frequency: {grid_frequency:0.2f} Hz")
        print(f"Inverter Efficiency: {inverter_efficiency:0.2f} %")
        print(f"Internal Temperature: {internal_temperature:0.1f} °C")
        
        print("\n--- Energy Generation ---")
        cumulative_power_generation = regs.get_value(RegName.CUMULATIVE_POWER_GENERATION)
        power_generation_day = regs.get_value(RegName.POWER_GENERATION_DAY)
        power_generation_month = regs.get_value(RegName.POWER_GENERATION_MONTH)
        power_generation_year = regs.get_value(RegName.POWER_GENERATION_YEAR)
        print(f"Cumulative Power Generation: {cumulative_power_generation:0.2f} kWh")
        print(f"Power Generation (Day): {power_generation_day:0.2f} kWh")
        print(f"Power Generation (Month): {power_generation_month:0.2f} kWh")
        print(f"Power Generation (Year): {power_generation_year:0.2f} kWh")
        
        print("\n--- Active Power Calculation ---")
        active_power_calculation = regs.get_value(RegName.ACTIVE_POWER_CALCULATION)
        print(f"Active Power Calculation: {active_power_calculation:0.2f} kW")

    def addr_diff(self, start_name, end_name):
        dif = self.regs.get(end_name).address - self.regs.get(start_name).address
        print(f"addre diff {dif}")
        return self.regs.get(end_name).address - self.regs.get(start_name).address + self.regs.get(end_name).get_size()


async def main():
    test = Tester()
    await test.run()


if __name__ == '__main__':
    asyncio.run(main())
