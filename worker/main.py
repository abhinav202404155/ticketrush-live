"""booking-worker: takes one booking request at a time off the queue and processes it.
Run more copies of this container = more bookings processed per second (this is what KEDA will do)."""
import json
import logging
import os
import time

import pika
from prometheus_client import Counter, start_http_server

from .db import pool
from .seat_logic import mark_failed, process_booking

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

RABBIT_URL = os.environ["RABBITMQ_URL"]
QUEUE = "booking_requests"
WORK_DELAY = int(os.getenv("WORK_DELAY_MS", "0")) / 1000
PROCESSED = Counter("worker_bookings_processed_total", "Bookings processed", ["result"])


def on_message(channel, method, properties, body):
    booking_id = json.loads(body)["booking_id"]
    try:
        time.sleep(WORK_DELAY)  # pretend work, so scaling is visible in demos
        result = process_booking(booking_id)
    except Exception:
        log.exception("booking %s crashed", booking_id)
        mark_failed(booking_id, "Internal error")
        result = "ERROR"
    PROCESSED.labels(result=result).inc()
    log.info("booking %s -> %s", booking_id, result)
    channel.basic_ack(delivery_tag=method.delivery_tag)  # ack AFTER finishing: crash = message is redelivered


def main():
    start_http_server(int(os.getenv("METRICS_PORT", "8000")))
    pool.open(wait=True, timeout=60)
    while True:  # reconnect loop: RabbitMQ may still be starting
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)  # fair dispatch: one message at a time per worker
            channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
            log.info("worker ready")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            log.warning("RabbitMQ not ready, retrying in 3s")
            time.sleep(3)


if __name__ == "__main__":
    main()
