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
    U1 = auto()
    U2 = auto()
    U3 = auto()
    UAVGLN = auto()

    UL1L2 = auto()
    UL2L3 = auto()
    UL3L1 = auto()

    UAVGLL = auto()

    I1 = auto()
    I2 = auto()
    I3 = auto()
    IAVG = auto()

    P1 = auto()
    P2 = auto()
    P3 = auto()
    PTOT = auto()

    Q1 = auto()
    Q2 = auto()
    Q3 = auto()
    QTOT = auto()

    SL1 = auto()
    SL2 = auto()
    SL3 = auto()
    SLTOT = auto()

    LAML1 = auto()
    LAML2 = auto()
    LAML3 = auto()
    LAMTOT = auto()

    F = auto()

    L13_ACT_ENERGY_IN = auto()
    L13_ACT_ENERGY_OUT = auto()
    L13_ACT_ENERGY_NET = auto()
    L13_ACT_ENERGY_TOT = auto()

    L13_REACT_ENERGY_IN = auto()
    L13_REACT_ENERGY_OUT = auto()
    L13_REACT_ENERGY_NET = auto()
    L13_REACT_ENERGY_TOT = auto()

    THD_UL1 = auto()
    THD_UL2 = auto()

    DMD_I1 = auto()
    DMD_I2 = auto()
    DMD_I3 = auto()
    DMD_PTOT = auto()
    DMD_QTOT = auto()
    DMD_STOT = auto()

    DMD_PRED_I1 = auto()
    DMD_PRED_I2 = auto()
    DMD_PRED_I3 = auto()
    DMD_PRED_PTOT = auto()
    DMD_PRED_QTOT = auto()
    DMD_PRED_STOT = auto()

    PT_PRIM = auto()
    PT_SEC = auto()
    CT_PRIM = auto()
    CT_SEC = auto()

    DMD_PERIOD = auto()
    DMD_WINDOWS = auto()
    DMD_DYNAMICS = auto()

    UNIX_TS = auto()

    CLEAR_CONCLUDED_LOGS = auto()
    CLEAR_ENERGY_LOGS = auto()
    CLEAR_ENERGY_MONTH_LOGS = auto()



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


class BenderRegs:
    BASE_ADDRESS = 0
    PLC_BASE_ADDRESS = "D300"

    def __init__(self):
        self.regs = {
            RegName.U1: Reg("U1", "u1", RegType.F32, 0),
            RegName.U2: Reg("U2", "u2", RegType.F32, 2),
            RegName.U3: Reg("U3", "u3", RegType.F32, 4),
            RegName.UAVGLN: Reg("Uln", "uln", RegType.F32, 6),

            RegName.UL1L2: Reg("UL1L2", "ul1l2", RegType.F32, 8),
            RegName.UL2L3: Reg("UL2L3", "ul2l3", RegType.F32, 10),
            RegName.UL3L1: Reg("UL3L1", "ul3l1", RegType.F32, 12),
            RegName.UAVGLL: Reg("Ull", "ull", RegType.F32, 14),

            RegName.I1: Reg("I1", "i1", RegType.F32, 16),
            RegName.I2: Reg("I2", "i2", RegType.F32, 18),
            RegName.I3: Reg("I3", "i3", RegType.F32, 20),
            RegName.IAVG: Reg("Iavg", "iavg", RegType.F32, 22),

            RegName.P1: Reg("P1", "p1", RegType.F32, 24),
            RegName.P2: Reg("P2", "p2", RegType.F32, 26),
            RegName.P3: Reg("P3", "p3", RegType.F32, 28),
            RegName.PTOT: Reg("Ptot", "ptot", RegType.F32, 30),

            RegName.Q1: Reg("Q1", "q1", RegType.F32, 32),
            RegName.Q2: Reg("Q2", "q2", RegType.F32, 34),
            RegName.Q3: Reg("Q3", "q3", RegType.F32, 36),
            RegName.QTOT: Reg("Qtot", "qtot", RegType.F32, 38),

            RegName.SL1: Reg("SL1", "q1", RegType.F32, 40),
            RegName.SL2: Reg("SL2", "q2", RegType.F32, 42),
            RegName.SL3: Reg("SL3", "q3", RegType.F32, 44),
            RegName.SLTOT: Reg("SLtot", "qtot", RegType.F32, 46),

            RegName.LAML1: Reg("LamL1", "laml1", RegType.F32, 48),
            RegName.LAML2: Reg("LamL2", "laml2", RegType.F32, 50),
            RegName.LAML3: Reg("LamL3", "laml3", RegType.F32, 52),
            RegName.LAMTOT: Reg("Lamtot", "lamtot", RegType.F32, 54),

            RegName.F: Reg("F", "f", RegType.F32, 56),

            RegName.L13_ACT_ENERGY_IN: Reg("L13 Active Energy In", "l13_active_energy_in", RegType.I32, 500, 0.1),
            RegName.L13_ACT_ENERGY_OUT: Reg("L13 Active Energy Out", "l13_active_energy_out", RegType.I32, 502, 0.1),
            RegName.L13_ACT_ENERGY_NET: Reg("L13 Active Energy Net", "l13_active_energy_net", RegType.I32, 504, 0.1),
            RegName.L13_ACT_ENERGY_TOT: Reg("L13 Active Energy Tot", "l13_active_energy_tot", RegType.I32, 506, 0.1),

            RegName.L13_REACT_ENERGY_IN: Reg("L13 Reactive Energy In", "l13_reactive_energy_in", RegType.I32, 508, 0.1),
            RegName.L13_REACT_ENERGY_OUT: Reg("L13 Reactive Energy Out", "l13_reactive_energy_out", RegType.I32, 510, 0.1),
            RegName.L13_REACT_ENERGY_NET: Reg("L13 Reactive Energy Net", "l13_reactive_energy_net", RegType.I32, 512, 0.1),
            RegName.L13_REACT_ENERGY_TOT: Reg("L13 Reactive Energy Tot", "l13_reactive_energy_tot", RegType.I32, 514, 0.1),

            RegName.THD_UL1: Reg("THD UL1", "thd_ul1", RegType.F32, 1600),
            RegName.THD_UL2: Reg("THD UL2", "thd_ul1", RegType.F32, 1602),

            RegName.DMD_I1: Reg("DMD I1", "dmd_i1", RegType.F32, 3000),
            RegName.DMD_I2: Reg("DMD I2", "dmd_i2", RegType.F32, 3002),
            RegName.DMD_I3: Reg("DMD I3", "dmd_i3", RegType.F32, 3004),
            RegName.DMD_PTOT: Reg("DMD PTOT", "dmd_ptot", RegType.F32, 3006, 0.001), # kWh
            RegName.DMD_QTOT: Reg("DMD QTOT", "dmd_qtot", RegType.F32, 3008, 0.001), # kWh
            RegName.DMD_STOT: Reg("DMD STOT", "dmd_stot", RegType.F32, 3010, 0.001),

            RegName.DMD_PRED_I1: Reg("DMD PROD I1", "dmd_prod_i1", RegType.F32, 3200),
            RegName.DMD_PRED_I2: Reg("DMD PROD I2", "dmd_prod_i2", RegType.F32, 3202),
            RegName.DMD_PRED_I3: Reg("DMD PROD I3", "dmd_prod_i3", RegType.F32, 3204),
            RegName.DMD_PRED_PTOT: Reg("DMD PROD PTOT", "dmd_prod_ptot", RegType.F32, 3206, 0.001),
            RegName.DMD_PRED_QTOT: Reg("DMD PROD QTOT", "dmd_prod_qtot", RegType.F32, 3208, 0.001),
            RegName.DMD_PRED_STOT: Reg("DMD PROD STOT", "dmd_prod_stot", RegType.F32, 3210, 0.001),

            RegName.PT_PRIM: Reg("PT Prim", "pt_prim", RegType.U32, 6000),
            RegName.PT_SEC: Reg("PT Sec", "pt_sec", RegType.U32, 6002),
            RegName.CT_PRIM: Reg("CT Prim", "ct_prim", RegType.U32, 6004),
            RegName.CT_SEC: Reg("CT Sec", "ct_sec", RegType.U32, 6006),


            RegName.DMD_PERIOD: Reg("DMD Period", "dmd_period", RegType.U16, 6029),
            RegName.DMD_WINDOWS: Reg("DMD Windows", "dmd_windows", RegType.U16, 6030),
            RegName.DMD_DYNAMICS: Reg("DMD Dynamics", "dmd_dynamics", RegType.U16, 6031),

            RegName.UNIX_TS: Reg("UNIX ts", "unix_ts", RegType.U32, 9004),

            RegName.CLEAR_CONCLUDED_LOGS: Reg("Clear concluded logs", "clear_concluded_logs", RegType.U16, 9600),
            RegName.CLEAR_ENERGY_LOGS: Reg("Clear energy logs", "clear_energy_logs", RegType.U16, 9601),
            RegName.CLEAR_ENERGY_MONTH_LOGS: Reg("Clear energy month logs", "clear_energy_month_logs", RegType.U16, 9602),

        }
        self.total_regs_count = self.calculate_regs_count()
        self.last_plant_data_addr = self.get(RegName.L13_ACT_ENERGY_OUT).address

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

