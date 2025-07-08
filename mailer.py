import asyncio
from smtplib import SMTP_SSL
import datetime

from config import Config


class Mailer:
    def __init__(self, smtp_server, smtp_port, username, password, from_addr):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.debuglevel = 0

    async def send_mail(self, to_addr, subj, message_text):
        def _send_mail_sync():
            smtp = SMTP_SSL(host='smtp.seznam.cz', port=465)
            smtp.connect('smtp.seznam.cz', 465)
            smtp.set_debuglevel(self.debuglevel)
            smtp.login(self.username, self.password)

            date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            msg = "From: %s\nTo: %s\nSubject: %s\nDate: %s\n\n%s" % (
                self.from_addr, to_addr, subj, date, message_text
            )

            smtp.sendmail(self.from_addr, to_addr, msg)
            smtp.quit()
            print("mail send DONE - " + subj)

        await asyncio.get_event_loop().run_in_executor(None, _send_mail_sync)



async def main():
    config = Config()
    mailer = Mailer(config.mail_smtp_server, config.mail_smtp_port, config.mail_username, config.mail_password, config.mail_from_addr)
    await mailer.send_mail(to_addr=config.smtp_to_addr, subj='Test Subject', message_text='This is a test message from the async mailer.')


if __name__ == "__main__":
    asyncio.run(main())



        