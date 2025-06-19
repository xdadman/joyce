import asyncio
import datetime
import json
import logging
from asyncio import CancelledError

import pytz
from pymodbus.client import AsyncModbusSerialClient


SERIAL_PORT = "SERIAL_PORT"
SERIAL_BAUDRATE = "SERIAL_BAUDRATE"
SERIAL_STOPBITS = "SERIAL_STOPBITS"
SERIAL_PARITY = "SERIAL_PARITY"

ESI_TZ = 'Europe/Prague'

from registers_bender import BenderRegs, RegName

SLAVE = 100

log = logging.getLogger(__name__)



class ModbusMeterClient:
    def __init__(self):
        self.client: AsyncModbusSerialClient = None
        self.cfg = {
            SERIAL_PORT: "/dev/ttyUSB0",
            SERIAL_BAUDRATE: 9600,
            SERIAL_STOPBITS: 1,
            SERIAL_PARITY: "E",
        }

    async def run(self):
        regs = BenderRegs()

        while True:
            # Wait until start of a minute
            #await self.wait_until_minute_start()

            # --------------------- make all readings -------------------------
            now = datetime.datetime.now(pytz.timezone(ESI_TZ))
            # Unix timestamp
            read_result5 = await self.client.read_holding_registers(9004, 2, slave=SLAVE)

            log.info("")
            log.info(f'Next round {now}')

            read_result = await self.client.read_holding_registers(0, 32, slave=SLAVE)
            read_result2 = await self.client.read_holding_registers(500, 16, slave=SLAVE)
            read_result3 = await self.client.read_holding_registers(1600, 4, slave=SLAVE)
            # Demand data
            read_result4 = await self.client.read_holding_registers(3000, 12, slave=SLAVE)
            read_result4a = await self.client.read_holding_registers(3200, 12, slave=SLAVE)

            read_result6 = await self.client.read_holding_registers(6000, 8, slave=SLAVE)
            # ------------------------- decode all reads --------------------------
            regs.decode(read_result.registers, 0, regs.get(RegName.PTOT).address)
            regs.decode(read_result2.registers, 500, regs.get(RegName.L13_REACT_ENERGY_TOT).address)
            regs.decode(read_result3.registers, 1600, regs.get(RegName.THD_UL2).address)
            regs.decode(read_result4.registers, 3000, regs.get(RegName.DMD_STOT).address)
            regs.decode(read_result4a.registers, 3200, regs.get(RegName.DMD_PRED_STOT).address)
            regs.decode(read_result5.registers, 9004, regs.get(RegName.UNIX_TS).address)
            regs.decode(read_result6.registers, 6000, regs.get(RegName.CT_SEC).address)

            # ------------------------ time check -------------------
            bender_ts = regs.get_value(RegName.UNIX_TS)
            bender_date = datetime.datetime.fromtimestamp(bender_ts, tz=pytz.timezone(ESI_TZ))

            await self.update_rtc_if_needed(regs, bender_ts, bender_date, now)

            u1 = round(regs.get_value(RegName.U1), 2)
            i1 = round(regs.get_value(RegName.I1), 2)
            p1 = round(regs.get_value(RegName.P1), 2)

            u2 = round(regs.get_value(RegName.U2), 2)
            i2 = round(regs.get_value(RegName.I2), 2)
            p2 = round(regs.get_value(RegName.P2), 2)

            u3 = round(regs.get_value(RegName.U3), 2)
            i3 = round(regs.get_value(RegName.I3), 2)
            p3 = round(regs.get_value(RegName.P3), 2)

            act_e_in = round(regs.get_value(RegName.L13_ACT_ENERGY_IN), 2)
            act_e_out = round(regs.get_value(RegName.L13_ACT_ENERGY_OUT), 2)

            react_e_in = round(regs.get_value(RegName.L13_REACT_ENERGY_IN), 2)
            react_e_out = round(regs.get_value(RegName.L13_REACT_ENERGY_OUT), 2)

            act_e_net = regs.get_value(RegName.L13_ACT_ENERGY_NET)
            act_e_tot = regs.get_value(RegName.L13_ACT_ENERGY_TOT)

            pt = f'{regs.get_value(RegName.PT_PRIM)}/{regs.get_value(RegName.PT_SEC)}'
            ct = f'{regs.get_value(RegName.CT_PRIM)}/{regs.get_value(RegName.CT_SEC)}'

            dmd_ptot = round(regs.get_value(RegName.DMD_PTOT), 4)
            dmd_pred_ptot = round(regs.get_value(RegName.DMD_PRED_PTOT), 4)

            dmd_per = regs.get_value(RegName.DMD_PERIOD)
            dmd_win = regs.get_value(RegName.DMD_WINDOWS)

            dmd_ts = self.start_of_last_ended_15_minute_period(bender_date)
            dmd_ts_str = self.format_datetime(dmd_ts)

            log.info(f'{u1:.2f}V {i1:.2f}A {p1:.2f}W EIn:{act_e_in:.2f}kWh Eout:{act_e_out:.2f}kWh Enet:{act_e_net:.2f}kWh Etot:{act_e_tot:.2f}kWh'
                  f' dmd_ptot:{dmd_ptot:.2f}kWh dmd_pred_tot:{dmd_pred_ptot:.2f}kWh  dmd_per:{dmd_per} dmd_win:{dmd_win} {bender_date}')
            #log.info(f'PT:{pt} CT: {ct} {date}')

            log.info(f'DmdPtot: {dmd_ptot:.4f}kW DmdPredPtot: {dmd_pred_ptot:.4f}kW DmdPeriod: {dmd_per} DmdWindows: {dmd_win} {bender_date}')

            log.info(f'XXX DmdPtot: {dmd_ptot:.4f}kW DmdPredPtot: {bender_date} {now} {dmd_ts}')

            ts_rounded = self.round_to_nearest_minute(now)
            ts_rounded_str = self.format_datetime(ts_rounded)
            msg_data = {
                'type': "meter",
                'esi_no': 1,
                'data': {
                    'u1': u1,
                    'u2': u2,
                    'u3': u3,

                    'i1': i1,
                    'i2': i2,
                    'i3': i3,

                    'p1': p1,
                    'p2': p2,
                    'p3': p3,

                    'e_act_in': act_e_in,
                    'e_act_out': act_e_out,

                    'e_react_in': react_e_in,
                    'e_react_out': react_e_out,

                    'dmd_ptot': dmd_ptot, # 15min (based od period, demand Ptot)
                    'dmd_pred_ptot': dmd_pred_ptot,  # 15min (based od period, demand Ptot)
                    'dmd_ts': dmd_ts_str, # Start of period of demand timestamp
                    'dmd_period': '15M',

                    'ts': ts_rounded_str
                }
            }
            msg = json.dumps(msg_data)
            print(msg)
            await asyncio.sleep(2)

    async def modbus_meter_client_task(self):
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
        try:
            await self.run()
        except Exception as e:
            log.error("modbus_meter_client_task Exception: " + str(e))
        except CancelledError as e:
            log.info("CancelledError modbus_meter_client_task leaving: " + str(e))
            return
        finally:
            log.info("kafka_db_sender_task finally")
        log.warning("Wait 10 sec")
        await asyncio.sleep(10)

    async def update_rtc_if_needed(self, regs: BenderRegs, ts, bender_now, now):
        delta = now - bender_now
        seconds = delta.seconds
        if abs(seconds) >= 2:
            log.info(f'Delta {delta} {seconds}s need to be updated')
            ts_now = int(now.timestamp())
            log.info(f'Bender: {ts} Esi: {ts_now}')

            # update now to actual state
            now = datetime.datetime.now(pytz.timezone(ESI_TZ))
            ts_now = int(now.timestamp())
            regs.set_value(RegName.UNIX_TS, ts_now)
            values = regs.encode(regs.get(RegName.UNIX_TS).address, regs.get(RegName.UNIX_TS).address)
            await self.client.write_registers(regs.get(RegName.UNIX_TS).address, values, slave=SLAVE)
        else:
            log.info(f'Delta {delta} {seconds}s OK')


    async def wait_until_minute_start(self):
        now = datetime.datetime.now(pytz.timezone(ESI_TZ))
        reserve_be_over_00 = datetime.timedelta(seconds=2)
        next_minute = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1) + reserve_be_over_00
        delay = (next_minute - now).total_seconds()
        log.info(f'{now} Wait: {delay}')
        await asyncio.sleep(delay)

    async def clear_energy_logs(self, regs: BenderRegs):
        #Clear energy logs
        regs.set_value(RegName.CLEAR_CONCLUDED_LOGS, 0xff00)
        regs.set_value(RegName.CLEAR_ENERGY_LOGS, 0xff00)
        regs.set_value(RegName.CLEAR_ENERGY_MONTH_LOGS, 0xff00)
        values = regs.encode(regs.get(RegName.CLEAR_CONCLUDED_LOGS).address, regs.get(RegName.CLEAR_ENERGY_MONTH_LOGS).address)
        await self.client.write_registers(regs.get(RegName.CLEAR_CONCLUDED_LOGS).address, values, slave=SLAVE)


    def round_to_nearest_minute(self, dt: datetime.datetime) -> datetime.datetime:
        # If seconds are 30 or more, add a minute and set seconds and microseconds to 0
        if dt.second >= 30:
            dt += datetime.timedelta(minutes=1)

        # Set seconds and microseconds to 0
        return dt.replace(second=0, microsecond=0)

    def format_datetime(self, dt: datetime.datetime) -> str:
        # Format the datetime part
        dt_str = dt.strftime('%Y-%m-%dT%H:%M:%S')

        # Add milliseconds
        milliseconds = f"{dt.microsecond // 1000:03d}"

        # Format the timezone part
        timezone = dt.strftime('%z')
        timezone = f"{timezone[:3]}:{timezone[3:]}"  # Change from +hhmm to +hh:mm

        # Combine all parts
        formatted = f"{dt_str}.{milliseconds}{timezone}"
        return formatted

    def start_of_last_ended_15_minute_period(self, dt: datetime.datetime) -> datetime.datetime:
        periods_since_hour_start = dt.minute // 15

        # Calculate the start of the last ended 15-minute period
        last_period_start_minutes = (periods_since_hour_start * 15) - 15

        # If we're at the start of the hour, wrap to the previous hour
        if last_period_start_minutes < 0:
            last_period_start_minutes = 45
            dt -= datetime.timedelta(hours=1)

        # Replace the minutes, seconds, and microseconds to get the start of the last ended 15-minute period
        rounded_dt = dt.replace(minute=last_period_start_minutes, second=0, microsecond=0)

        return rounded_dt

    async def set_ct_prim_sec(self, regs: BenderRegs):
        regs.set_value(RegName.CT_PRIM, 6)
        values = regs.encode(regs.get(RegName.CT_PRIM).address, regs.get(RegName.CT_PRIM).address)
        log.info(f'values {values}')
        await self.client.write_registers(regs.get(RegName.CT_PRIM).address, values, slave=SLAVE)

        regs.set_value(RegName.CT_SEC, 4)
        values = regs.encode(regs.get(RegName.CT_SEC).address, regs.get(RegName.CT_SEC).address)
        log.info(f'values {values}')
        await self.client.write_registers(regs.get(RegName.CT_SEC).address, values, slave=SLAVE)