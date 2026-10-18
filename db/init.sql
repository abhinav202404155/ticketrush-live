-- Runs once, when the Postgres container is first created.
-- events = the thing people want to see. shows = one session of an event (venue + city + date/time).
CREATE TABLE users (
  id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE events (
  id SERIAL PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, language TEXT NOT NULL,
  genre TEXT NOT NULL, duration_min INTEGER NOT NULL, rating NUMERIC(2,1) NOT NULL, age_rating TEXT NOT NULL,
  base_price INTEGER NOT NULL, featured BOOLEAN NOT NULL DEFAULT false,
  description TEXT NOT NULL, image_url TEXT   -- image_url optional: paste any image link to replace the generated poster
);

CREATE TABLE shows (
  id SERIAL PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id),
  venue TEXT NOT NULL, city TEXT NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL, opens_at TIMESTAMPTZ NOT NULL,  -- opens_at = flash release time
  price_inr INTEGER NOT NULL
);
CREATE INDEX shows_event_idx ON shows(event_id);

CREATE TABLE bookings (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), show_id INTEGER NOT NULL REFERENCES shows(id),
  seat_ids INTEGER[] NOT NULL, status TEXT NOT NULL,  -- QUEUED | HELD | CONFIRMED | FAILED | EXPIRED
  reason TEXT, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX bookings_status_idx ON bookings(status);
CREATE INDEX bookings_user_idx ON bookings(user_id);

CREATE TABLE seats (
  id SERIAL PRIMARY KEY, show_id INTEGER NOT NULL REFERENCES shows(id), label TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'AVAILABLE', held_until TIMESTAMPTZ, booking_id INTEGER REFERENCES bookings(id),
  UNIQUE (show_id, label)
);
CREATE INDEX seats_show_idx ON seats(show_id);

-- All titles below are fictional (original names only).
INSERT INTO events (title, category, language, genre, duration_min, rating, age_rating, base_price, featured, description) VALUES
('Midnight Monsoon','Movies','Hindi','Drama',142,8.4,'UA',250,true,'Two strangers share one taxi and one long, rain-soaked night in Mumbai.'),
('Stand-Up Saturday','Comedy','English','Stand-up',95,8.1,'16+',399,true,'Five of the sharpest new comics, one stage, zero filters.'),
('Neon Nights Rock Fest','Concerts','English','Rock',180,9.2,'All ages',999,true,'Flash drop! The biggest rock night of the year. Seats open at the set time.'),
('The Last Lighthouse','Movies','English','Thriller',118,7.9,'UA',280,true,'A keeper on a remote island finds the light is guiding something else home.'),
('Chai & Chaos','Movies','Hindi','Comedy',126,7.6,'U',230,false,'A tiny tea stall, three feuding families and one very bad wedding plan.'),
('Orbit Nine','Movies','English','Sci-Fi',151,8.6,'UA',320,true,'The crew of a lonely station gets a message from their own future.'),
('Kaveri Express','Movies','Tamil','Action',139,8.0,'UA',260,false,'A midnight train, a stolen file and forty minutes to the next station.'),
('Hyderabad Heist','Movies','Telugu','Action',147,7.8,'UA',260,false,'A crew of old friends plan one last job in the old city.'),
('Paper Kites','Movies','Hindi','Family',112,8.3,'U',220,false,'A boy, a rooftop and the kite that finally changes his neighbourhood.'),
('Sufi Sunset Sessions','Concerts','Hindi','Sufi',150,8.8,'All ages',699,false,'Qawwali and soft light as the sun goes down. Bring a shawl.'),
('Electro Monsoon DJ Night','Concerts','English','Electronic',240,8.2,'18+',799,false,'Four DJs, one dance floor and a very loud rainstorm of bass.'),
('Indie Lanterns Live','Concerts','English','Indie',165,8.5,'All ages',599,false,'Seven rising indie bands play under a thousand paper lanterns.'),
('Classical Fusion Evening','Concerts','Hindi','Fusion',130,8.7,'All ages',549,false,'Sitar, violin and tabla trade solos in a one-night-only fusion set.'),
('The Roast Room','Comedy','English','Roast',90,7.9,'18+',449,false,'Comics roast each other, then roast you. Sit at your own risk.'),
('Improv Night Live','Comedy','Hindi','Improv',85,8.0,'16+',349,false,'Every scene is invented live from your suggestions.'),
('City Derby: Football','Sports','English','Football',120,9.0,'All ages',350,true,'The two biggest local clubs meet again. Floodlights, drums, derby day.'),
('Premier Kabaddi Night','Sports','Hindi','Kabaddi',130,8.4,'All ages',250,false,'Fast raids, loud crowds and a final that goes down to the last tackle.'),
('Street Cricket Cup Finals','Sports','English','Cricket',150,8.2,'All ages',299,false,'Gully cricket champions from six cities play for the cup.'),
('The Glass Palace','Theatre','English','Play',130,8.6,'UA',450,false,'A family drama staged in a house made entirely of mirrors.'),
('Gully Stars: The Musical','Theatre','Hindi','Musical',150,8.7,'U',550,false,'Street kids chase a dream of the big stage, with twelve original songs.'),
('Pottery & Chai Workshop','Workshops','English','Craft',120,8.5,'All ages',499,false,'Learn the wheel, make your own cup, then fill it with chai.'),
('Photography Walk','Workshops','English','Photography',150,8.3,'16+',399,false,'A guided golden-hour walk with a pro. Bring any camera or phone.'),
('Beginner Salsa Night','Workshops','English','Dance',90,8.1,'18+',349,false,'No partner needed. Learn the basics, then dance till late.');

-- First three sessions are fixed (the tests rely on them). Show 3 is the "flash release" that opens in 1 hour.
INSERT INTO shows (event_id, venue, city, starts_at, opens_at, price_inr) VALUES
 (1,'Aurora Cinemas','Mumbai', now() + interval '5 days',  now() - interval '1 day', 250),
 (2,'The Laugh Loft','Mumbai', now() + interval '6 days',  now() - interval '1 day', 399),
 (3,'Skyline Arena','Mumbai',  now() + interval '30 days', now() + interval '1 hour', 999);

-- Bulk sessions: each event plays in 3 cities, for the next 4 days, at 11:00 and 19:30 IST.
INSERT INTO shows (event_id, venue, city, starts_at, opens_at, price_inr)
SELECT e.id, k.venue, c.city,
       ((current_date + d) + tt.t::time) AT TIME ZONE 'Asia/Kolkata',
       now() - interval '1 day',
       e.base_price + (d % 2) * 50
FROM events e
CROSS JOIN (VALUES ('Mumbai',0),('Delhi',1),('Bengaluru',2),('Hyderabad',3),('Pune',4),('Chennai',5)) AS c(city, i)
CROSS JOIN (VALUES ('Aurora Cinemas','Movies'),('Skyline Arena','Concerts'),('Skyline Arena','Sports'),
                   ('The Laugh Loft','Comedy'),('The Laugh Loft','Theatre'),('The Laugh Loft','Workshops')) AS k(venue, cat)
CROSS JOIN generate_series(1, 4) AS d
CROSS JOIN (VALUES ('11:00'),('19:30')) AS tt(t)
WHERE k.cat = e.category AND e.id <> 3 AND ((c.i - e.id) % 6 + 6) % 6 < 3;

INSERT INTO seats (show_id, label)
SELECT s.id, r.rw || n::text
FROM shows s
CROSS JOIN (VALUES ('A'),('B'),('C'),('D'),('E'),('F')) AS r(rw)
CROSS JOIN generate_series(1, 10) AS n;
