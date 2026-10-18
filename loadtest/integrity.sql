-- After a load test: double_booked_seats must be 0, and seats_sold must equal sold_seats_in_confirmed_bookings.
SELECT 'double_booked_seats' AS check, COUNT(*) AS value FROM (
  SELECT s FROM (SELECT unnest(seat_ids) AS s FROM bookings WHERE status = 'CONFIRMED') x GROUP BY s HAVING COUNT(*) > 1) d
UNION ALL SELECT 'confirmed_bookings', COUNT(*) FROM bookings WHERE status = 'CONFIRMED'
UNION ALL SELECT 'seats_sold', COUNT(*) FROM seats WHERE status = 'SOLD'
UNION ALL SELECT 'sold_seats_in_confirmed_bookings', COALESCE(SUM(cardinality(seat_ids)), 0) FROM bookings WHERE status = 'CONFIRMED';
