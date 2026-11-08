import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / "app.py"


class LogisticsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = Path(folder.name) / "test.sqlite3"

    def invoke(self, *args):
        return subprocess.run(
            [sys.executable, str(APP), "--db", str(self.db), *args],
            capture_output=True, text=True, check=False,
        )

    def run_command(self, *args):
        result = self.invoke(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_order_reaches_delivered_with_persistent_history(self):
        code = self.run_command("create", "Demo manzil")["code"]
        self.run_command("receive", code)
        self.run_command("assign", code, "Demo kuryer")
        self.run_command("dispatch", code)
        self.run_command("deliver", code)
        tracking = self.run_command("track", code.lower())
        self.assertEqual(tracking["status"], "Yetkazildi")
        self.assertEqual(
            [event["status"] for event in tracking["history"]],
            ["Yangi", "Omborda", "Yo‘lda", "Yetkazildi"],
        )
        self.assertNotIn("Demo manzil", json.dumps(tracking))
        self.assertNotIn("Demo kuryer", json.dumps(tracking))

    def test_cannot_skip_assignment_or_change_history(self):
        code = self.run_command("create", "Demo manzil")["code"]
        self.run_command("receive", code)
        self.assertEqual(self.invoke("dispatch", code).returncode, 2)
        self.assertEqual(self.run_command("track", code)["status"], "Omborda")

    def test_unknown_tracking_code_returns_a_clear_error(self):
        result = self.invoke("track", "UNKNOWN")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Buyurtma topilmadi", result.stderr)

    def test_blank_address_and_unknown_warehouse_are_rejected(self):
        self.assertEqual(self.invoke("create", "   ").returncode, 2)
        self.assertEqual(self.invoke("create", "Demo", "--warehouse", "999").returncode, 2)


if __name__ == "__main__":
    unittest.main()
