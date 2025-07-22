import asyncio
import datetime
import json
import logging
from typing import List

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder

from cloud_sender import CloudSender
from common import setup_logging
from config import Config
from event_sender import EventSender
from influx import InfluxWriter
from invertor import Invertor
from mailer import Mailer
from msgdb import MsgDb
from registers_goodwe_ht import GoodweHTRegs, RegName, RegType
from rtu_monitor import RtuMonitor

log = logging.getLogger(__name__)

HT_NOMINAL_POWER = 110 # kW
ROUND_SEC = 300 


class GoodweHTSet:
    def __init__(self, config: Config, influx_writer: InfluxWriter, rtu_monitor: RtuMonitor, event_sender: EventSender, cloud_sender: CloudSender):
        self.config = config
        self.invertors: List[Invertor] = self.invertors_from_cfg()
        self.influx_writer = influx_writer
        self.rtu_monitor: RtuMonitor = rtu_monitor
        self.event_sender: EventSender = event_sender
        self.cloud_sender: CloudSender = cloud_sender
        self.regs = GoodweHTRegs() # only for addressing purposes, not for data
        self.db = MsgDb()

    def invertors_from_cfg(self) -> List[Invertor]:
        invertors = []
        invertor_no = 1
        for slave in self.config.modbus_slaves:
            invertors.append(Invertor(invertor_no, slave))
            invertor_no += 1
        return invertors

    async def start_socat(self):
        log.info("Starting socat")
        cmd = ["socat", "PTY,link=/tmp/ttyVirtual,raw,echo=0", "TCP:10.71.0.4:2000"]
        #cmd = ["socat", "PTY,link=/tmp/ttyVirtual,raw,echo=0", "TCP:10.76.1.48:2000"]
        import subprocess
        subprocess.Popen(cmd)
        await asyncio.sleep(2)
        log.info("Started socat")

    async def run(self):

        await self.event_sender.send_event(f"Started Invertor Monitor {self.config.plant}")

        self.client = AsyncModbusSerialClient(
            port=self.config.serial_device,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
        )

        if self.config.serial_device == "/tmp/ttyVirtual":
            await self.start_socat()

        await self.client.connect()

        await self.db.connect()

        while True:
            log.info(f"=== Cycle === {datetime.datetime.now()}")

            # Read regulation setup from RTU
            power_adjust = None
            try:
                # Read percent regulation from RTU signals (0%, 30%, 60%, 100%)
                regulation = await self.rtu_monitor.read_requested_regulation()
                power_adjust = int(regulation * HT_NOMINAL_POWER / 100)
                log.info(f"Power adjust: {power_adjust} from regulation {regulation}")

                for invertor in self.invertors:
                    try:
                        actual_power_adjust = await self.get_actual_power_adjust(invertor)
                        if actual_power_adjust != power_adjust:
                            log.info(f"Need update power adjust {actual_power_adjust} in invertor {invertor}, RTU request: {power_adjust}")
                            await self.set_actual_power_adjust(invertor, power_adjust)
                            await self.event_sender.send_event(f"Updated Power Adjust {self.config.plant} to {power_adjust}")
                        else:
                            log.info(f"Skip power adjust {actual_power_adjust} in invertor {invertor}, actual is the same.")
                    except Exception as e:
                        log.error(f"Error in reading/setting regulation for {invertor}: {e}")
                        await self.event_sender.send_event(f"Error in reading/setting regulation for {self.config.plant} {invertor}", f"{e}")
            except Exception as e:
                # TODO - toto nechceme, chceme nastavit 100% i kdyz nejede
                log.error(f"Exception getting/setting RTU regulation: {e}, skipping power regulation...")
                await self.event_sender.send_event(f"Error in reading/setting regulation for {self.config.plant}", f"{e}")

            # Standard invertor monitoring
            try:
                for invertor in self.invertors:
                    log.info(f"Invertor round: {invertor}")
                    try:
                        regs = await self.read_invertor_regs(invertor)
                        self.print_invertor_regs(regs)

                        # convert regs to json
                        json_str = self.generate_invetor_regs_json(regs, invertor, self.config)
                        print(json_str)

                        await self.db.insert_message("data", json_str)

                        try:
                            await self.cloud_sender.send(json_str)
                        except Exception as e:
                            log.error(f"Failed to write to Cloud: {e}")

                        try:
                            self.write_influx_invertor_regs(regs, invertor)
                            log.info("Data successfully written to InfluxDB")
                        except Exception as e:
                            log.error(f"Failed to write to InfluxDB: {e}")
                            await self.event_sender.send_event(f"Failed to write to InfluxDB: {e}")
                    except Exception as e:
                        log.error(f"Failed to process invertor monitoring {invertor}: {e}")
                        await self.event_sender.send_event(f"Failed to process invertor monitoring {invertor}: {e}")

                # Read pending messages from db and send them, max 50 at a time
                count = 0
                while True:
                    try:
                        msg = await self.db.pending_msg_get()
                        if not msg:
                            log.info("No other messages")
                            break
                        count += 1
                        await self.db.update_done(msg)
                        if count == 50:
                            log.info(f"Skipping next pending message after {count}, will be processed next round")
                            break

                    except Exception as e:
                        log.error(f"Exception getting msg from db and sending to cloud: {e}")
                        break


            except Exception as e:
                log.error(f"Error in reading cycle: {e}")
                await self.event_sender.send_event(f"Error in reading cycle: {e}")
                
            log.info(f"Waiting {ROUND_SEC} seconds before next cycle...")
            await asyncio.sleep(ROUND_SEC)

    def addr_diff(self, start_name, end_name):
        dif = self.regs.get(end_name).address - self.regs.get(start_name).address
        #log.info(f"address diff {dif}")
        return self.regs.get(end_name).address - self.regs.get(start_name).address + self.regs.get(end_name).get_size()

    async def get_actual_power_adjust(self, invertor: Invertor):
        if not invertor.power_adjust:
            invertor.power_adjust = await self.read_invertor_power_adjust(invertor)
        return invertor.power_adjust

    async def read_invertor_power_adjust(self, invertor: Invertor):
        slave = invertor.slave_address
        result_adjust = await self.client.read_holding_registers(41480, 1, slave=slave)
        decoder = BinaryPayloadDecoder.fromRegisters(result_adjust.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        power_adjust = decoder.decode_16bit_uint()
        log.info(f"Read Actual Power adjust for {slave} is {power_adjust}")
        return power_adjust

    async def set_actual_power_adjust(self, invertor: Invertor, power_adjust: int):
        await self.write_invertor_power_adjust(invertor, power_adjust)
        invertor.power_adjust = power_adjust

    async def write_invertor_power_adjust(self, invertor: Invertor, power_adjust: int):
        log.info(f"Writing invertor power adjust: {power_adjust} to {invertor}")
        slave = invertor.slave_address
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        builder.add_16bit_uint(power_adjust)
        registers = builder.to_registers()
        # TODO - remove to set it
        await self.client.write_registers(41480, registers, slave=slave)


    async def read_invertor_regs(self, invertor: Invertor) -> GoodweHTRegs:
        regs = GoodweHTRegs()
        slave = invertor.slave_address
        result0 = await self.client.read_holding_registers(32002, 1, slave=slave)
        result1 = await self.client.read_holding_registers(32016, self.addr_diff(RegName.PV1_U, RegName.INTERNAL_TEMPERATURE), slave=slave)
        result2 = await self.client.read_holding_registers(32106, self.addr_diff(RegName.CUMULATIVE_POWER_GENERATION, RegName.POWER_GENERATION_YEAR), slave=slave)
        result3 = await self.client.read_holding_registers(35502, regs.get(RegName.SERIAL_NUMBER).multiplier, slave=slave)
        result_rtc = await self.client.read_holding_registers(41313, self.addr_diff(RegName.RTC_YEAR_MONTH, RegName.RTC_MINUTE_SECOND), slave=slave)

        regs.decode(result0.registers, regs.get(RegName.OPER_STATUS).address, regs.get(RegName.OPER_STATUS).address)
        regs.decode(result1.registers, regs.get(RegName.PV1_U).address, regs.get(RegName.INTERNAL_TEMPERATURE).address)
        regs.decode(result2.registers, regs.get(RegName.CUMULATIVE_POWER_GENERATION).address, regs.get(RegName.POWER_GENERATION_YEAR).address)
        regs.decode(result3.registers, regs.get(RegName.SERIAL_NUMBER).address, regs.get(RegName.SERIAL_NUMBER).address)
        regs.decode(result_rtc.registers, regs.get(RegName.RTC_YEAR_MONTH).address, regs.get(RegName.RTC_MINUTE_SECOND).address)
        return regs

    def print_invertor_regs(self, regs: GoodweHTRegs):
        status = regs.get_value(RegName.OPER_STATUS)
        log.info(f"Invertor status: {status}")

        # for i in range(1, 25):
        #     pv_u_name = getattr(RegName, f"PV{i}_U")
        #     pv_c_name = getattr(RegName, f"PV{i}_C")
        #
        #     pv_u = regs.get_value(pv_u_name)
        #     pv_c = regs.get_value(pv_c_name)
        #
        #     log.info(f"PV{i}: {pv_u:0.1f}V {pv_c:0.2f}A")


        input_power = regs.get_value(RegName.INPUT_POWER)
        log.info(f"Input Power: {input_power:0.2f} kW")

        grid_ab_voltage = regs.get_value(RegName.GRID_AB_VOLTAGE)
        grid_bc_voltage = regs.get_value(RegName.GRID_BC_VOLTAGE)
        grid_ca_voltage = regs.get_value(RegName.GRID_CA_VOLTAGE)
        log.info(f"Grid Line Voltages - AB: {grid_ab_voltage:0.1f}V, BC: {grid_bc_voltage:0.1f}V, CA: {grid_ca_voltage:0.1f}V")

        grid_a_voltage = regs.get_value(RegName.GRID_A_VOLTAGE)
        grid_b_voltage = regs.get_value(RegName.GRID_B_VOLTAGE)
        grid_c_voltage = regs.get_value(RegName.GRID_C_VOLTAGE)
        log.info(f"Grid Phase Voltages - A: {grid_a_voltage:0.1f}V, B: {grid_b_voltage:0.1f}V, C: {grid_c_voltage:0.1f}V")

        grid_a_current = regs.get_value(RegName.GRID_A_CURRENT)
        grid_b_current = regs.get_value(RegName.GRID_B_CURRENT)
        grid_c_current = regs.get_value(RegName.GRID_C_CURRENT)
        log.info(f"Grid Currents - A: {grid_a_current:0.3f}A, B: {grid_b_current:0.3f}A, C: {grid_c_current:0.3f}A")

        peak_active_power_day = regs.get_value(RegName.PEAK_ACTIVE_POWER_DAY)
        active_power = regs.get_value(RegName.ACTIVE_POWER)
        reactive_power = regs.get_value(RegName.REACTIVE_POWER)
        power_factor = regs.get_value(RegName.POWER_FACTOR)
        log.info(f"Peak Active Power (Day): {peak_active_power_day:0.2f} kW")
        log.info(f"Active Power: {active_power:0.2f} kW")
        log.info(f"Reactive Power: {reactive_power:0.2f} kvar")
        log.info(f"Power Factor: {power_factor:0.3f}")

        grid_frequency = regs.get_value(RegName.GRID_FREQUENCY)
        inverter_efficiency = regs.get_value(RegName.INVERTER_EFFICIENCY)
        internal_temperature = regs.get_value(RegName.INTERNAL_TEMPERATURE)
        log.info(f"Grid Frequency: {grid_frequency:0.2f} Hz")
        log.info(f"Inverter Efficiency: {inverter_efficiency:0.2f} %")
        log.info(f"Internal Temperature: {internal_temperature:0.1f} °C")

        cumulative_power_generation = regs.get_value(RegName.CUMULATIVE_POWER_GENERATION)
        power_generation_day = regs.get_value(RegName.POWER_GENERATION_DAY)
        power_generation_month = regs.get_value(RegName.POWER_GENERATION_MONTH)
        power_generation_year = regs.get_value(RegName.POWER_GENERATION_YEAR)
        log.info(f"Cumulative Power Generation: {cumulative_power_generation:0.2f} kWh")
        #print(f"Power Generation (Day): {power_generation_day:0.2f} kWh")
        #print(f"Power Generation (Month): {power_generation_month:0.2f} kWh")
        #print(f"Power Generation (Year): {power_generation_year:0.2f} kWh")

        active_power_calculation = regs.get_value(RegName.ACTIVE_POWER_CALCULATION)
        #log.info(f"Active Power Calculation: {active_power_calculation:0.2f} kW")


        serial_number = regs.get_value(RegName.SERIAL_NUMBER)
        print(f"Serial Number: {serial_number}")

        rtc_year_month = regs.get_value(RegName.RTC_YEAR_MONTH)
        rtc_day_hour = regs.get_value(RegName.RTC_DAY_HOUR)
        rtc_minute_second = regs.get_value(RegName.RTC_MINUTE_SECOND)

        year = (rtc_year_month >> 8) & 0xFF
        month = rtc_year_month & 0xFF
        day = (rtc_day_hour >> 8) & 0xFF
        hour = rtc_day_hour & 0xFF
        minute = (rtc_minute_second >> 8) & 0xFF
        second = rtc_minute_second & 0xFF

        # Convert 2-digit year to 4-digit (assuming 20xx)
        full_year = 2000 + year if year >= 15 else 2000 + year

        log.info(f"Device RTC: {full_year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}")
        log.info(f"Raw Values - Year/Month: 0x{rtc_year_month:04X}, Day/Hour: 0x{rtc_day_hour:04X}, Minute/Second: 0x{rtc_minute_second:04X}")

    def write_influx_invertor_regs(self, regs: GoodweHTRegs, invertor: Invertor):
        if self.influx_writer:
            self.influx_writer.write_regs(regs, invertor)

    def generate_invetor_regs_json(self, regs: GoodweHTRegs, invertor: Invertor, config: Config) -> str:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        iso_string = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        rtc_year_month = regs.get_value(RegName.RTC_YEAR_MONTH)
        rtc_day_hour = regs.get_value(RegName.RTC_DAY_HOUR)
        rtc_minute_second = regs.get_value(RegName.RTC_MINUTE_SECOND)

        year = (rtc_year_month >> 8) & 0xFF
        month = rtc_year_month & 0xFF
        day = (rtc_day_hour >> 8) & 0xFF
        hour = rtc_day_hour & 0xFF
        minute = (rtc_minute_second >> 8) & 0xFF
        second = rtc_minute_second & 0xFF

        # Convert 2-digit year to 4-digit (assuming 20xx)
        full_year = 2000 + year if year >= 15 else 2000 + year

        rtc = f"{full_year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

        data = {
            "plant": config.plant,
            "invertor_no": invertor.invertor_no,
            "invertor_typ": "goodwe-ht",
            "slave_address": invertor.slave_address,
            "power_adjust": invertor.power_adjust,
            "timestamp": iso_string,
            "rtc": rtc
        }
        
        for reg in regs.regs.values():
            if reg.json_name not in regs.skip_names:
                if reg.typ != RegType.STR:
                    data[reg.json_name] = round(reg.value, 2)
                else:
                    data[reg.json_name] = reg.value
            
        return json.dumps(data, indent=2)



async def main():
    setup_logging(log_level=logging.INFO)

    config = Config()
    influx_writer = InfluxWriter(
        url="http://10.76.0.1:8087",
        token="token",
        org="myorg",
        bucket="ht"
    )
    rtu_monitor = RtuMonitor(config.adam_ip)
    config = Config()
    mailer = Mailer(config.mail_smtp_server, config.mail_smtp_port, config.mail_username, config.mail_password, config.mail_from_addr)
    event_sender = EventSender(mailer, config.mail_to_addr)
    cloud_sender = CloudSender(config.cloud_svc_url)
    test = GoodweHTSet(config, influx_writer, rtu_monitor, event_sender, cloud_sender)
    await test.run()


if __name__ == '__main__':
    asyncio.run(main())
