import asyncio

from advantech_adam import AdamDevice
from config import Config


class RtuMonitor:
    def __init__(self, adam_ip: str):
        self.adam = AdamDevice(adam_ip)
        self.connected = False


    # Method returns requested regulation in percent 0- full reguilation, 100 - no regulation
    async def read_requested_regulation(self) -> int:
        try:
            if not self.connected:
                await self.adam.connect()
                self.connected = True
        except Exception as e:
            print(f"Error while connecting to ADAM: {e}")
            return None

        try:
            inputs = await self.adam.read_digital_inputs(count=4)
            regulation = self.inputs_to_regulation(inputs)
            print(f"regulation = {regulation} inputs: {inputs}")
            return regulation
        except Exception as e:
            print(f"Error while getting inputs from ADAM: {e}")
            self.connected = False
            return None

    # When input is swtiched on then its False, if is not switched, then its True
    def inputs_to_regulation(self, inputs: list[bool]) -> int:
        i1, i2, i3, i4 = inputs

        if not i1:
            return 0
        if not i2:
            return 30
        if not i3:
            return 60
        if not i4:
            return 100
        print("Defaulting not set RTU switch to 100")
        return 100


async def main():
    cfg = Config()
    rtu_decoder = RtuMonitor(cfg.adam_ip)

    while True:
        regulation = await rtu_decoder.read_requested_regulation()
        print(f"regulation: {regulation}")
        await asyncio.sleep(1)


if __name__ == '__main__':
    mon = RtuMonitor(None)

    inputs = [True, True, True, True]
    expected_value = 100
    regulation = mon.inputs_to_regulation(inputs)
    print(f"regulation: {regulation} for {inputs}")
    assert regulation == expected_value, f"Expected {expected_value}, got {regulation}"

    inputs = [True, True, True, False]
    expected_value = 100
    regulation = mon.inputs_to_regulation(inputs)
    print(f"regulation: {regulation} for {inputs}")
    assert regulation == expected_value, f"Expected {expected_value}, got {regulation}"

    inputs = [True, True, False, True]
    expected_value = 60
    regulation = mon.inputs_to_regulation(inputs)
    print(f"regulation: {regulation} for {inputs}")
    assert regulation == expected_value, f"Expected {expected_value}, got {regulation}"

    inputs = [True, False, True, True]
    expected_value = 30
    regulation = mon.inputs_to_regulation(inputs)
    print(f"regulation: {regulation} for {inputs}")
    assert regulation == expected_value, f"Expected {expected_value}, got {regulation}"

    inputs = [False, True, True, True]
    expected_value = 0
    regulation = mon.inputs_to_regulation(inputs)
    print(f"regulation: {regulation} for {inputs}")
    assert regulation == expected_value, f"Expected {expected_value}, got {regulation}"

    #asyncio.run(main())
