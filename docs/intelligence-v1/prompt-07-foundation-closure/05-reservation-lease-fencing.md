# Reservation lease fencing

Reservations carry an owner token, generation, reservation time, expiry, and reclaim time. Expired reservations can be reclaimed with a new generation/token; finalization requires the live fence when one exists, so a late worker cannot finalize the reclaimed lease.
