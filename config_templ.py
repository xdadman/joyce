class Config:
    def __init__(self):
        self.plant = "otnice"
        self.modbus_slaves = [1, 2, 3, 4]
        self.cloud_svc_url = "http://joycare.joyce.cz:58081/goodweht/saveinverterdata/v1.0"
        self.serial_device = "/dev/ttyAMA2"
        self.adam_ip = "192.168.0.116"


        self.mail_smtp_server="your.server.com"
        self.mail_smtp_port=465
        self.mail_username="your_username"
        self.mail_password="your_password"

        self.mail_from_addr = "Joyce Goodwe Monitor <your@mail>"
        self.mail_to_addr = "your@mail_tosend_to.com"
