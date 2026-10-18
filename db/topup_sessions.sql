-- Adds sessions for the next 30 days (and their seats). Safe to run any time and as often as you like:
-- sessions/seats that already exist are skipped. Run it about every 3-4 weeks on the live database.
INSERT INTO shows (event_id, venue, city, starts_at, opens_at, price_inr)
SELECT e.id, k.venue, c.city,
       ((current_date + d) + tt.t::time) AT TIME ZONE 'Asia/Kolkata', now() - interval '1 day', e.base_price + (d % 2) * 50
FROM events e
CROSS JOIN (VALUES ('Mumbai',0),('Delhi',1),('Bengaluru',2),('Hyderabad',3),('Pune',4),('Chennai',5)) AS c(city, i)
CROSS JOIN (VALUES ('Aurora Cinemas','Movies'),('Skyline Arena','Concerts'),('Skyline Arena','Sports'),
                   ('The Laugh Loft','Comedy'),('The Laugh Loft','Theatre'),('The Laugh Loft','Workshops')) AS k(venue, cat)
CROSS JOIN generate_series(1, 30) AS d
CROSS JOIN (VALUES ('11:00'),('19:30')) AS tt(t)
WHERE k.cat = e.category AND e.id <> 3 AND ((c.i - e.id) % 6 + 6) % 6 < 3
  AND NOT EXISTS (SELECT 1 FROM shows x WHERE x.event_id = e.id AND x.city = c.city AND x.venue = k.venue
                  AND x.starts_at = ((current_date + d) + tt.t::time) AT TIME ZONE 'Asia/Kolkata');

INSERT INTO seats (show_id, label)
SELECT s.id, r.rw || n::text
FROM shows s
CROSS JOIN (VALUES ('A'),('B'),('C'),('D'),('E'),('F')) AS r(rw)
CROSS JOIN generate_series(1, 10) AS n
WHERE NOT EXISTS (SELECT 1 FROM seats z WHERE z.show_id = s.id);
