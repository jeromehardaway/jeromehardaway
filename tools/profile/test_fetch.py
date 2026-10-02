from datetime import date

from fetch import streaks

today = date(2026, 10, 2)
# today empty: current streak ends yesterday
assert streaks({"2026-09-30": 1, "2026-10-01": 2}, today) == (2, 2)
# today counted; longest run elsewhere
assert streaks({"2026-01-01": 1, "2026-01-02": 1, "2026-01-03": 1, "2026-10-02": 1}, today) == (1, 3)
# gap of two days breaks it
assert streaks({"2026-09-29": 1}, today) == (0, 1)
print("ok")
