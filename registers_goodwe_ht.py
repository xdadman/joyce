from __future__ import annotations

import math
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


class RegName(Enum):
    OPER_STATUS = auto()
    PV1_U = auto()
    PV1_C = auto()
    PV2_U = auto()
    PV2_C = auto()



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
                print("Encoding space %d" % self.values[i])
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
        else:
            raise Exception("Unsupported type " + str(self.typ))
        if self.multiplier:
            self.value *= self.multiplier

    def encode(self, builder: BinaryPayloadBuilder):
        reg_val = self.value
        if self.multiplier:
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
            RegName.PV1_C: Reg("PV1_C", "pv2_c", RegType.I16, 32017, 0.1),
            RegName.PV2_U: Reg("PV2_U", "pv1_u", RegType.I16, 32018, 0.1),
            RegName.PV2_C: Reg("PV2_C", "pv2_c", RegType.I16, 32019, 0.1),
        }
        self.total_regs_count = self.calculate_regs_count()
        self.last_plant_data_addr = self.get(RegName.PV2_C).address

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
                reg.decode(decoder)
                reg.print()

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

