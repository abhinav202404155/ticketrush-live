-- Runs once, when the Postgres container is first created.
CREATE TABLE users (
  id            SERIAL PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE shows (
  id          SERIAL PRIMARY KEY,
  title       TEXT NOT NULL,
  venue       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  starts_at   TIMESTAMPTZ NOT NULL,
  opens_at    TIMESTAMPTZ NOT NULL,   -- booking opens here (flash release)
  price_inr   INTEGER NOT NULL
);

CREATE TABLE bookings (
  id         SERIAL PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id),
  show_id    INTEGER NOT NULL REFERENCES shows(id),
  seat_ids   INTEGER[] NOT NULL,
  status     TEXT NOT NULL,  -- QUEUED | HELD | CONFIRMED | FAILED | EXPIRED
  reason     TEXT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX bookings_status_idx ON bookings(status);
CREATE INDEX bookings_user_idx ON bookings(user_id);

CREATE TABLE seats (
  id         SERIAL PRIMARY KEY,
  show_id    INTEGER NOT NULL REFERENCES shows(id),
  label      TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'AVAILABLE',  -- AVAILABLE | HELD | SOLD
  held_until TIMESTAMPTZ,
  booking_id INTEGER REFERENCES bookings(id),
  UNIQUE (show_id, label)
);

-- Demo data (original names only)
INSERT INTO shows (title, venue, description, starts_at, opens_at, price_inr) VALUES
 ('Midnight Jazz Night', 'Lakeside Arena', 'An evening of live jazz.', now() + interval '10 days', now() - interval '1 day', 499),
 ('Stand-Up Saturday',   'City Hall',      'Five comedians, one stage.', now() + interval '14 days', now() - interval '1 day', 299),
 ('Flash Release: Rock Fest', 'Open Ground', 'Limited seats, opens soon!', now() + interval '30 days', now() + interval '1 hour', 999);

INSERT INTO seats (show_id, label)
SELECT s.id, r.rw || n::text
FROM shows s
CROSS JOIN (VALUES ('A'),('B'),('C'),('D'),('E')) AS r(rw)
CROSS JOIN generate_series(1, 10) AS n;
