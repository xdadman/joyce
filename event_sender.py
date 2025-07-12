import logging

from mailer import Mailer

logger = logging.getLogger(__name__)

class EventSender:
    def __init__(self, mailer: Mailer, to_address: str):
        self.mailer = mailer
        self.to_address = to_address

    async def send_event(self, subject: str, body: str = None):
        try:
            if not body:
                body = subject
            await self.mailer.send_mail(self.to_address, subject, body)
        except Exception as e:
            logger.error(f"Error sending event {body} {e}")


