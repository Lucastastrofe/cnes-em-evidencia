import unittest
from pathlib import Path


class DailyUpdateWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.workflow = (root / ".github" / "workflows" / "update-data.yml").read_text(
            encoding="utf-8"
        )

    def test_every_successful_check_publishes_its_audit_metadata(self):
        self.assertIn("git add data/published", self.workflow)
        self.assertNotIn("steps.changes.outputs.changed", self.workflow)
        self.assertNotIn("source_hash=$old_hash", self.workflow)


if __name__ == "__main__":
    unittest.main()
