from __future__ import absolute_import
import os,json,logging,redis

from .worker import app

from .discord import run_bot

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True)


@app.task(bind=True, name='run_bot_exe', default_retry_delay=10)
def run_bot_exe(self, nonce):
    try:
        run_bot(nonce)
    except Exception as exc:
        raise self.retry(exc=exc)


