import asyncio
import logging

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

from config import Config

log = logging.getLogger(__name__)

class Mailer:
    def __init__(self, smtp_server, smtp_port, username, password, from_addr):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr

    async def send_mail(self, to_addr, subj, message_text):
        message = MIMEMultipart()
        message["From"] = self.from_addr
        message["To"] = to_addr
        message["Subject"] = subj
        message["Date"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        message.attach(MIMEText(message_text, "plain"))

        await aiosmtplib.send(
            message,
            hostname=self.smtp_server,
            port=self.smtp_port,
            username=self.username,
            password=self.password,
            use_tls=True
        )
        
        log.info(f"Sent mail {subj}")



async def main():
    config = Config()
    mailer = Mailer(config.mail_smtp_server, config.mail_smtp_port, config.mail_username, config.mail_password, config.mail_from_addr)
    await mailer.send_mail(to_addr=config.mail_to_addr, subj='Test Subject', message_text='This is a test message from the async mailer.')


if __name__ == "__main__":
    asyncio.run(main())



        