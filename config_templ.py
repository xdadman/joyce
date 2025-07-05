class Config:
    def __init__(self):
        self.plant = "otnice"
        self.modbus_slaves = [1, 2, 3, 4]
        #self.modbus_slaves = [1]
        self.cloud_svc_url = "http://xxx.cz"
        #self.serial_device = "/tmp/ttyVirtual"
        self.serial_device = "/tmp/ttyAMA2"
        self.adam_ip = "10.71.0.4"
