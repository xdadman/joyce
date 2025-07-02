from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
from datetime import datetime, timezone

from invertor import Invertor
from registers_goodwe_ht import GoodweHTRegs, RegName

log = logging.getLogger(__name__)

class InfluxWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        
    def write_regs(self, regs: GoodweHTRegs, invertor: Invertor):
        """Write PV power values to InfluxDB measurement 'power'"""
        try:
            points = []
            timestamp = datetime.now(timezone.utc)
            
            # Write power for all PV1-PV24
            for i in range(1, 25):
                pv_u_name = getattr(RegName, f"PV{i}_U")
                pv_c_name = getattr(RegName, f"PV{i}_C")
                
                pv_voltage = regs.get_value(pv_u_name)
                pv_current = regs.get_value(pv_c_name)
                pv_power = pv_voltage * pv_current
                
                # Create power point for each PV
                power_point = Point("power") \
                    .tag("invertor_no", f"inv{invertor.invertor_no}") \
                    .tag("pv", f"pv{i}") \
                    .field("value", pv_power) \
                    .time(timestamp)
                points.append(power_point)
            
            # Write additional power measurements
            additional_powers = [
                ("input_power", RegName.INPUT_POWER),
                ("active_power", RegName.ACTIVE_POWER),
                ("reactive_power", RegName.REACTIVE_POWER)
            ]
            
            for power_type, reg_name in additional_powers:
                power_value = regs.get_value(reg_name)
                power_point = Point("power") \
                    .tag("invertor_no", f"inv{invertor.invertor_no}") \
                    .tag("pv", power_type) \
                    .field("value", power_value) \
                    .time(timestamp)
                points.append(power_point)
            
            # Write grid voltage data
            grid_voltages = [
                ("grid_a", RegName.GRID_A_VOLTAGE),
                ("grid_b", RegName.GRID_B_VOLTAGE),
                ("grid_c", RegName.GRID_C_VOLTAGE)
            ]
            
            for phase_name, reg_name in grid_voltages:
                voltage_value = regs.get_value(reg_name)
                voltage_point = Point("grid_voltages") \
                    .tag("invertor_no", f"inv{invertor.invertor_no}") \
                    .tag("phase", phase_name) \
                    .field("value", voltage_value) \
                    .time(timestamp)
                points.append(voltage_point)
            
            # Write grid current data
            grid_currents = [
                ("grid_a", RegName.GRID_A_CURRENT),
                ("grid_b", RegName.GRID_B_CURRENT),
                ("grid_c", RegName.GRID_C_CURRENT)
            ]
            
            for phase_name, reg_name in grid_currents:
                current_value = regs.get_value(reg_name)
                current_point = Point("grid_current") \
                    .tag("invertor_no", f"inv{invertor.invertor_no}") \
                    .tag("phase", phase_name) \
                    .field("value", current_value) \
                    .time(timestamp)
                points.append(current_point)
            
            # Write stats data as a single point with multiple fields
            stats_point = Point("stats") \
                .tag("invertor_no", f"inv{invertor.invertor_no}") \
                .field("power_factor", regs.get_value(RegName.POWER_FACTOR)) \
                .field("grid_frequency", regs.get_value(RegName.GRID_FREQUENCY)) \
                .field("inverter_efficiency", regs.get_value(RegName.INVERTER_EFFICIENCY)) \
                .field("internal_temperature", regs.get_value(RegName.INTERNAL_TEMPERATURE)) \
                .time(timestamp)
            points.append(stats_point)
            
            # Write all points to InfluxDB
            self.write_api.write(bucket=self.bucket, record=points)
            log.info(f"Written power data for PV1-PV24, additional powers, grid voltages, grid currents, and stats to InfluxDB")
            
        except Exception as e:
            log.error(f"Error writing to InfluxDB: {e}")
            raise
    
    def close(self):
        """Close the InfluxDB client connection"""
        if self.client:
            self.client.close()