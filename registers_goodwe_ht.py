from __future__ import annotations

import math
import traceback
from enum import Enum, auto
import sys

import logging
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian

log = logging.getLogger(__name__)

debug_space_registers = False

class RegType(Enum):
    U16 = 1
    I16 = 2
    U32 = 3
    I32 = 4
    F32 = 5
    STR = 6


class RegName(Enum):
    OPER_STATUS = auto()
    PV1_U = auto()
    PV1_C = auto()
    PV2_U = auto()
    PV2_C = auto()
    PV3_U = auto()
    PV3_C = auto()
    PV4_U = auto()
    PV4_C = auto()
    PV5_U = auto()
    PV5_C = auto()
    PV6_U = auto()
    PV6_C = auto()
    PV7_U = auto()
    PV7_C = auto()
    PV8_U = auto()
    PV8_C = auto()
    PV9_U = auto()
    PV9_C = auto()
    PV10_U = auto()
    PV10_C = auto()
    PV11_U = auto()
    PV11_C = auto()
    PV12_U = auto()
    PV12_C = auto()
    PV13_U = auto()
    PV13_C = auto()
    PV14_U = auto()
    PV14_C = auto()
    PV15_U = auto()
    PV15_C = auto()
    PV16_U = auto()
    PV16_C = auto()
    PV17_U = auto()
    PV17_C = auto()
    PV18_U = auto()
    PV18_C = auto()
    PV19_U = auto()
    PV19_C = auto()
    PV20_U = auto()
    PV20_C = auto()
    PV21_U = auto()
    PV21_C = auto()
    PV22_U = auto()
    PV22_C = auto()
    PV23_U = auto()
    PV23_C = auto()
    PV24_U = auto()
    PV24_C = auto()
    INPUT_POWER = auto()
    GRID_AB_VOLTAGE = auto()
    GRID_BC_VOLTAGE = auto()
    GRID_CA_VOLTAGE = auto()
    GRID_A_VOLTAGE = auto()
    GRID_B_VOLTAGE = auto()
    GRID_C_VOLTAGE = auto()
    GRID_A_CURRENT = auto()
    GRID_B_CURRENT = auto()
    GRID_C_CURRENT = auto()
    PEAK_ACTIVE_POWER_DAY = auto()
    ACTIVE_POWER = auto()
    REACTIVE_POWER = auto()
    POWER_FACTOR = auto()
    GRID_FREQUENCY = auto()
    INVERTER_EFFICIENCY = auto()
    INTERNAL_TEMPERATURE = auto()
    CUMULATIVE_POWER_GENERATION = auto()
    POWER_GENERATION_DAY = auto()
    POWER_GENERATION_MONTH = auto()
    POWER_GENERATION_YEAR = auto()
    ACTIVE_POWER_CALCULATION = auto()

    SERIAL_NUMBER = auto()

    RTC_YEAR_MONTH = auto()
    RTC_DAY_HOUR = auto()
    RTC_MINUTE_SECOND = auto()



class Space:
    def __init__(self, name:str, address: int, size: int):
        self.name: str = name
        self.address = address
        self.size = size
        self.values = [0] * size

    def get_size(self):
        return self.size

    def encode(self, builder: BinaryPayloadBuilder):
        for i in range(0, self.size):
            if self.values[i]:
                log.info("Encoding space %d" % self.values[i])
            builder.add_16bit_uint(self.values[i])

    def decode(self, decoder: BinaryPayloadDecoder):
        for i in range(0, self.size):
            val = decoder.decode_16bit_uint()
            self.values[i] = val
            if debug_space_registers and val != 0:
                log.info("Not empty space on " + str(self) + " pos: " + str(i) + " --> " + "D" + str(300 + i + self.address))

    def __str__(self):
        return self.name + " addr: " + str(self.address)

    def print(self):
        log.debug(self.name)


class Reg:
    def __init__(self, name: str, json_name: str, typ: RegType, address: int, multiplier: float = None):
        self.name: str = name
        self.typ: RegType = typ
        self.address = address
        self.json_name = json_name
        self.value = 0
        self.multiplier = multiplier

    def __str__(self):
        return self.name + " " + str(self.typ) + " addr: " + str(self.address)

    def get_size(self):
        if self.typ == RegType.U16:
            return 1
        if self.typ == RegType.I16:
            return 1
        if self.typ == RegType.U32:
            return 2
        if self.typ == RegType.I32:
            return 2
        if self.typ == RegType.F32:
            return 2
        if self.typ == RegType.STR:
            return self.multiplier
        raise Exception("Unsupported type " + str(self.typ))

    def decode(self, decoder: BinaryPayloadDecoder):
        if self.typ == RegType.U16:
            self.value = decoder.decode_16bit_uint()
        elif self.typ == RegType.I16:
            self.value = decoder.decode_16bit_int()
        elif self.typ == RegType.U32:
            self.value = decoder.decode_32bit_uint()
        elif self.typ == RegType.I32:
            self.value = decoder.decode_32bit_int()
        elif self.typ == RegType.F32:
            self.value = decoder.decode_32bit_float()
            if math.isnan(self.value):
                log.error("Nan value received in " + self.name)
                self.value = 0.0
            if math.isinf(self.value):
                log.error("Inf value received in " + self.name)
                self.value = 0.0
        elif self.typ == RegType.STR:

            string_length = int(self.multiplier)
            raw_values = []
            for _ in range(string_length):
                raw_values.append(decoder.decode_16bit_uint())

            chars = []
            for val in raw_values:
                high_byte = (val >> 8) & 0xFF
                low_byte = val & 0xFF
                if high_byte > 0:
                    chars.append(chr(high_byte))
                if low_byte > 0:
                    chars.append(chr(low_byte))

            self.value = ''.join(chars).rstrip('\x00')
        else:
            raise Exception("Unsupported type " + str(self.typ))
        if self.multiplier and self.typ != RegType.STR:
            self.value *= self.multiplier

    def encode(self, builder: BinaryPayloadBuilder):
        reg_val = self.value
        if self.multiplier and self.typ != RegType.STR:
            reg_val /= self.multiplier
        if self.typ == RegType.U16:
            builder.add_16bit_uint(int(reg_val))
        elif self.typ == RegType.I16:
            builder.add_16bit_int(int(reg_val))
        elif self.typ == RegType.U32:
            builder.add_32bit_uint(int(reg_val))
        elif self.typ == RegType.I32:
            builder.add_32bit_int(int(reg_val))
        elif self.typ == RegType.F32:
            builder.add_32bit_float(reg_val)
        elif self.typ == RegType.STR:
            string_length = self.multiplier if self.multiplier else 8
            string_val = str(reg_val) if reg_val else ""
            
            values = []
            for i in range(0, len(string_val), 2):
                high_byte = ord(string_val[i]) if i < len(string_val) else 0
                low_byte = ord(string_val[i + 1]) if i + 1 < len(string_val) else 0
                values.append((high_byte << 8) | low_byte)
            
            while len(values) < string_length:
                values.append(0)
            
            for val in values:
                builder.add_16bit_uint(val)
        else:
            raise Exception("Unsupported type " + str(self.typ))

    def print(self):
        log.debug(self.name + ": " + str(self.value))


class GoodweHTRegs:
    BASE_ADDRESS = 0
    PLC_BASE_ADDRESS = "D300"

    def __init__(self):
        self.regs = {
            RegName.OPER_STATUS: Reg("Operation status", "operation_status", RegType.U16, 32002),
            RegName.PV1_U: Reg("PV1_U", "pv1_u", RegType.I16, 32016, 0.1),
            RegName.PV1_C: Reg("PV1_C", "pv1_c", RegType.I16, 32017, 0.01),
            RegName.PV2_U: Reg("PV2_U", "pv2_u", RegType.I16, 32018, 0.1),
            RegName.PV2_C: Reg("PV2_C", "pv2_c", RegType.I16, 32019, 0.01),
            RegName.PV3_U: Reg("PV3_U", "pv3_u", RegType.I16, 32020, 0.1),
            RegName.PV3_C: Reg("PV3_C", "pv3_c", RegType.I16, 32021, 0.01),
            RegName.PV4_U: Reg("PV4_U", "pv4_u", RegType.I16, 32022, 0.1),
            RegName.PV4_C: Reg("PV4_C", "pv4_c", RegType.I16, 32023, 0.01),
            RegName.PV5_U: Reg("PV5_U", "pv5_u", RegType.I16, 32024, 0.1),
            RegName.PV5_C: Reg("PV5_C", "pv5_c", RegType.I16, 32025, 0.01),
            RegName.PV6_U: Reg("PV6_U", "pv6_u", RegType.I16, 32026, 0.1),
            RegName.PV6_C: Reg("PV6_C", "pv6_c", RegType.I16, 32027, 0.01),
            RegName.PV7_U: Reg("PV7_U", "pv7_u", RegType.I16, 32028, 0.1),
            RegName.PV7_C: Reg("PV7_C", "pv7_c", RegType.I16, 32029, 0.01),
            RegName.PV8_U: Reg("PV8_U", "pv8_u", RegType.I16, 32030, 0.1),
            RegName.PV8_C: Reg("PV8_C", "pv8_c", RegType.I16, 32031, 0.01),
            RegName.PV9_U: Reg("PV9_U", "pv9_u", RegType.I16, 32032, 0.1),
            RegName.PV9_C: Reg("PV9_C", "pv9_c", RegType.I16, 32033, 0.01),
            RegName.PV10_U: Reg("PV10_U", "pv10_u", RegType.I16, 32034, 0.1),
            RegName.PV10_C: Reg("PV10_C", "pv10_c", RegType.I16, 32035, 0.01),
            RegName.PV11_U: Reg("PV11_U", "pv11_u", RegType.I16, 32036, 0.1),
            RegName.PV11_C: Reg("PV11_C", "pv11_c", RegType.I16, 32037, 0.01),
            RegName.PV12_U: Reg("PV12_U", "pv12_u", RegType.I16, 32038, 0.1),
            RegName.PV12_C: Reg("PV12_C", "pv12_c", RegType.I16, 32039, 0.01),
            RegName.PV13_U: Reg("PV13_U", "pv13_u", RegType.I16, 32040, 0.1),
            RegName.PV13_C: Reg("PV13_C", "pv13_c", RegType.I16, 32041, 0.01),
            RegName.PV14_U: Reg("PV14_U", "pv14_u", RegType.I16, 32042, 0.1),
            RegName.PV14_C: Reg("PV14_C", "pv14_c", RegType.I16, 32043, 0.01),
            RegName.PV15_U: Reg("PV15_U", "pv15_u", RegType.I16, 32044, 0.1),
            RegName.PV15_C: Reg("PV15_C", "pv15_c", RegType.I16, 32045, 0.01),
            RegName.PV16_U: Reg("PV16_U", "pv16_u", RegType.I16, 32046, 0.1),
            RegName.PV16_C: Reg("PV16_C", "pv16_c", RegType.I16, 32047, 0.01),
            RegName.PV17_U: Reg("PV17_U", "pv17_u", RegType.I16, 32048, 0.1),
            RegName.PV17_C: Reg("PV17_C", "pv17_c", RegType.I16, 32049, 0.01),
            RegName.PV18_U: Reg("PV18_U", "pv18_u", RegType.I16, 32050, 0.1),
            RegName.PV18_C: Reg("PV18_C", "pv18_c", RegType.I16, 32051, 0.01),
            RegName.PV19_U: Reg("PV19_U", "pv19_u", RegType.I16, 32052, 0.1),
            RegName.PV19_C: Reg("PV19_C", "pv19_c", RegType.I16, 32053, 0.01),
            RegName.PV20_U: Reg("PV20_U", "pv20_u", RegType.I16, 32054, 0.1),
            RegName.PV20_C: Reg("PV20_C", "pv20_c", RegType.I16, 32055, 0.01),
            RegName.PV21_U: Reg("PV21_U", "pv21_u", RegType.I16, 32056, 0.1),
            RegName.PV21_C: Reg("PV21_C", "pv21_c", RegType.I16, 32057, 0.01),
            RegName.PV22_U: Reg("PV22_U", "pv22_u", RegType.I16, 32058, 0.1),
            RegName.PV22_C: Reg("PV22_C", "pv22_c", RegType.I16, 32059, 0.01),
            RegName.PV23_U: Reg("PV23_U", "pv23_u", RegType.I16, 32060, 0.1),
            RegName.PV23_C: Reg("PV23_C", "pv23_c", RegType.I16, 32061, 0.01),
            RegName.PV24_U: Reg("PV24_U", "pv24_u", RegType.I16, 32062, 0.1),
            RegName.PV24_C: Reg("PV24_C", "pv24_c", RegType.I16, 32063, 0.01),
            RegName.INPUT_POWER: Reg("Input Power", "input_power", RegType.I32, 32064, 0.001),
            RegName.GRID_AB_VOLTAGE: Reg("Grid AB Voltage", "grid_ab_voltage", RegType.U16, 32066, 0.1),
            RegName.GRID_BC_VOLTAGE: Reg("Grid BC Voltage", "grid_bc_voltage", RegType.U16, 32067, 0.1),
            RegName.GRID_CA_VOLTAGE: Reg("Grid CA Voltage", "grid_ca_voltage", RegType.U16, 32068, 0.1),
            RegName.GRID_A_VOLTAGE: Reg("Grid A Voltage", "grid_a_voltage", RegType.U16, 32069, 0.1),
            RegName.GRID_B_VOLTAGE: Reg("Grid B Voltage", "grid_b_voltage", RegType.U16, 32070, 0.1),
            RegName.GRID_C_VOLTAGE: Reg("Grid C Voltage", "grid_c_voltage", RegType.U16, 32071, 0.1),
            RegName.GRID_A_CURRENT: Reg("Grid A Current", "grid_a_current", RegType.I32, 32072, 0.001),
            RegName.GRID_B_CURRENT: Reg("Grid B Current", "grid_b_current", RegType.I32, 32074, 0.001),
            RegName.GRID_C_CURRENT: Reg("Grid C Current", "grid_c_current", RegType.I32, 32076, 0.001),
            RegName.PEAK_ACTIVE_POWER_DAY: Reg("Peak Active Power Day", "peak_active_power_day", RegType.I32, 32078, 0.001),
            RegName.ACTIVE_POWER: Reg("Active Power", "active_power", RegType.I32, 32080, 0.001),
            RegName.REACTIVE_POWER: Reg("Reactive Power", "reactive_power", RegType.I32, 32082, 0.001),
            RegName.POWER_FACTOR: Reg("Power Factor", "power_factor", RegType.I16, 32084, 0.001),
            RegName.GRID_FREQUENCY: Reg("Grid Frequency", "grid_frequency", RegType.U16, 32085, 0.01),
            RegName.INVERTER_EFFICIENCY: Reg("Inverter Efficiency", "inverter_efficiency", RegType.U16, 32086, 0.01),
            RegName.INTERNAL_TEMPERATURE: Reg("Internal Temperature", "internal_temperature", RegType.I16, 32087, 0.1),

            RegName.CUMULATIVE_POWER_GENERATION: Reg("Cumulative Power Generation", "cumulative_power_generation", RegType.U32, 32106, 0.01),
            RegName.POWER_GENERATION_DAY: Reg("Power Generation Day", "power_generation_day", RegType.U32, 32114, 0.01),
            RegName.POWER_GENERATION_MONTH: Reg("Power Generation Month", "power_generation_month", RegType.U32, 32116, 0.01),
            RegName.POWER_GENERATION_YEAR: Reg("Power Generation Year", "power_generation_year", RegType.U32, 32118, 0.01),
            RegName.ACTIVE_POWER_CALCULATION: Reg("Active Power Calculation", "active_power_calculation", RegType.I32, 32180, 1), #0.001),

            RegName.SERIAL_NUMBER: Reg("Serial Number", "serial_number", RegType.STR, 35502, 8),


            RegName.RTC_YEAR_MONTH: Reg("RTC Year/Month", "rtc_year_month", RegType.U16, 41313),
            RegName.RTC_DAY_HOUR: Reg("RTC Day/Hour", "rtc_day_hour", RegType.U16, 41314),
            RegName.RTC_MINUTE_SECOND: Reg("RTC Minute/Second", "rtc_minute_second", RegType.U16, 41315),
        }
        self.total_regs_count = self.calculate_regs_count()
        self.last_plant_data_addr = self.get(RegName.ACTIVE_POWER_CALCULATION).address
        self.skip_names = ["power_generation_day", "power_generation_month", "power_generation_year", "active_power_calculation", "rtc_year_month", "rtc_day_hour", "rtc_minute_second"]

    def set_value(self, name: RegName, value):
        reg: Reg = self.regs[name]
        reg.value = value

    def get_value(self, name: RegName):
        reg: Reg = self.regs[name]
        return reg.value

    def get(self, name: RegName):
        reg: Reg = self.regs[name]
        return reg


    def check_consitency(self):
        cnt_size = 0
        check_addr = self.BASE_ADDRESS
        consistent = True
        for reg in self.regs.values():
            if reg.address != check_addr:
                consistent = False
                log.error("RTU ADDR MISMATCH " + str(reg) + " NOT " + str(check_addr))
            check_addr += reg.get_size()
        if consistent:
            log.info("Registers Consitency OK, count: " + str(self.total_regs_count))
        else:
            log.error("Registers Not consistent, exiting")
            sys.exit(-1)

    def decode(self, values, address_from: int, address_to: int):
        decoder = BinaryPayloadDecoder.fromRegisters(values, byteorder=Endian.BIG, wordorder=Endian.BIG)
        for reg in self.regs.values():
            if address_from <= reg.address <= address_to:
                #print(reg)
                reg.decode(decoder)
                #reg.print()

    def encode(self, address_from: int, address_to: int) -> list:
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        for reg in self.regs.values():
            if address_from <= reg.address <= address_to:
                try:
                    reg.encode(builder)
                except Exception as e:
                    log.error(reg.json_name)
                    log.error(e)
                    raise e

        registers = builder.to_registers()
        return registers

    def calculate_regs_count(self) -> int:
        count = 0
        for reg in self.regs.values():
            count += reg.get_size()
        return count

    def get_last_address(self) -> int:
        reg = list(self.regs.values())[-1]
        return reg.address

    def print_values(self):
        for reg in self.regs.values():
            if isinstance(reg, Reg):
                if isinstance(reg.value, float):
                    log.info(reg.json_name + ": " + ("%0.2f" % reg.value) + " - " + str(reg.typ).replace("RegType.",""))
                else:
                    log.info(reg.json_name + ": " + str(reg.value) + " - " + str(reg.typ).replace("RegType.",""))
            else:
                log.info(".")

    def get_range(self, reg_from_name:RegName, reg_to_name: RegName) -> (int, int, int):
        reg_from = self.get(reg_from_name)
        reg_to = self.get(reg_to_name)
        count = reg_to.address + reg_to.get_size() - reg_from.address
        return reg_from.address, reg_to.address, count

