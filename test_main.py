import unittest
from datetime import datetime

import main


class AttendanceAppTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "číslo čipu": "1001",
                "zaměstnanec": "Adam Novák",
                "příchod": datetime(2026, 10, 12, 7, 2),
                "odchod": datetime(2026, 10, 12, 15, 17),
            },
            {
                "číslo čipu": "1001",
                "zaměstnanec": "Adam Novák",
                "příchod": datetime(2026, 10, 13, 7, 23),
                "odchod": datetime(2026, 10, 13, 15, 28),
            },
            {
                "číslo čipu": "1002",
                "zaměstnanec": "Barbora Svobodová",
                "příchod": datetime(2026, 10, 12, 8, 10),
                "odchod": datetime(2026, 10, 12, 16, 40),
            },
        ]

    def test_employee_summary_counts_worked_hours(self):
        summary = main.calculate_employee_summary(self.records)
        adam = next(item for item in summary if item["zaměstnanec"] == "Adam Novák")
        self.assertAlmostEqual(adam["práce_hodin"], 16.33, places=2)
        self.assertAlmostEqual(adam["průměrně_hodin"], 8.17, places=2)

    def test_late_minutes_are_counted(self):
        summary = main.calculate_employee_summary(self.records)
        barbara = next(item for item in summary if item["zaměstnanec"] == "Barbora Svobodová")
        self.assertEqual(barbara["zpoždění_minut"], 10)

    def test_daily_summary_aggregates_hours(self):
        daily = main.calculate_daily_summary(self.records)
        self.assertEqual(len(daily), 2)
        self.assertAlmostEqual(daily[0]["celkem_hodin"], 16.75, places=2)


if __name__ == "__main__":
    unittest.main()
