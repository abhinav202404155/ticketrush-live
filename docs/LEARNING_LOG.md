# Learning log
## Part 1
- What: backend services, queue, worker. Key terms: transaction, row lock, 202 Accepted, durable queue, ack, JWT, bcrypt.
- Interview line: "Booking requests go onto a RabbitMQ queue; workers lock seat rows with SELECT FOR UPDATE in a fixed order,
  so two buyers can never get the same seat, and I proved it with a 100-way concurrency test."
