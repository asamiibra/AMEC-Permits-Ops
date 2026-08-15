# Register count root cause

Lane counts and visible rows were computed through duplicated filtering paths. This made it possible for the badges to show stale, partial, or fake zero values while the table displayed a different result. The frontend also used `0` as the loading/error fallback, masking contract or transport failures.

The fix centralizes global search, Client, Activity, Location, Stage, and lane handling in one backend predicate. Counts are computed from the globally filtered set; the selected lane is then applied to the returned visible rows. The response identifies the contract as `bd-proposal-register-v2`. The UI shows an ellipsis while loading, an em dash on controlled error, and rows only after a valid response.
