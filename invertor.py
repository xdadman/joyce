class Invertor:
    def __init__(self, invertor_no: int, slave_address: int):
        self.invertor_no = invertor_no
        self.slave_address = slave_address

    def __str__(self):
        return f"Slave: {self.slave_address}"
