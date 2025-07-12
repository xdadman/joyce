import asyncio
import logging
import json
import os
from datetime import datetime, timedelta

from common import setup_logging
from config import Config
from mailer import Mailer

logger = logging.getLogger(__name__)

MAX_EVENTS_PER_HOUR = 10

class EventSender:
    def __init__(self, mailer: Mailer, to_address: str):
        self.mailer = mailer
        self.to_address = to_address
        self.state_file = "db/event_sender.state"

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning(f"Could not load state from {self.state_file}")
        return {"sent_times": []}
    
    def _save_state(self, state):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except IOError as e:
            logger.error(f"Could not save state to {self.state_file}: {e}")
    
    def _is_quiet_hours(self):
        current_time = datetime.now()
        hour = current_time.hour
        return hour >= 20 or hour < 7
    
    def _can_send_event(self):
        if self._is_quiet_hours():
            return False
            
        state = self._load_state()
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        recent_sends = [
            datetime.fromisoformat(timestamp) 
            for timestamp in state.get("sent_times", [])
            if datetime.fromisoformat(timestamp) > one_hour_ago
        ]

        return len(recent_sends) < MAX_EVENTS_PER_HOUR
    
    def _record_send(self):
        state = self._load_state()
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        state["sent_times"] = [
            timestamp for timestamp in state.get("sent_times", [])
            if datetime.fromisoformat(timestamp) > one_hour_ago
        ]
        
        state["sent_times"].append(current_time.isoformat())
        self._save_state(state)

    async def send_event(self, subject: str, body: str = None):
        logger.info(f"Sending event to {self.to_address} {subject}")
        if self._is_quiet_hours():
            logger.info("Event blocked during quiet hours (20:00-07:00)")
            return False
            
        if not self._can_send_event():
            logger.warning(f"Event rate limit exceeded. Maximum {MAX_EVENTS_PER_HOUR} events per hour allowed.")
            return False
        
        try:
            if not body:
                body = subject
            await self.mailer.send_mail(self.to_address, subject, body)
            self._record_send()
            return True
        except Exception as e:
            logger.error(f"Error sending event {body} {e}")
            return False

async def main():
    setup_logging(log_level=logging.INFO)
    config = Config()
    mailer = Mailer(config.mail_smtp_server, config.mail_smtp_port, config.mail_username, config.mail_password, config.mail_from_addr)
    event_sender = EventSender(mailer, config.mail_to_addr)

    for i in range(0, 12):
        await event_sender.send_event(f"Event {i}")


if __name__ == "__main__":
    asyncio.run(main())


