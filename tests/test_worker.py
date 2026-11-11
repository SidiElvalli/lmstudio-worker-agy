"""
Verification tests for LM Studio Worker MCP Server.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import get_worker_status, list_local_models, delegate_coding_task


class TestLMStudioWorker(unittest.TestCase):

    def test_status_check(self):
        status = get_worker_status()
        self.assertIn("status", status)
        print(f"\n[Status Check] Status: {status.get('status')}")
        if status.get("status") == "online":
            print(f"Loaded models: {status.get('available_models')}")

    def test_list_models(self):
        models = list_local_models()
        self.assertIsInstance(models, list)
        print(f"\n[Model Listing] Found {len(models)} models.")

    def test_delegation_if_online(self):
        status = get_worker_status()
        if status.get("status") != "online":
            self.skipTest("LM Studio local server is offline.")

        test_file = Path(__file__).parent / "output_test.py"
        try:
            result = delegate_coding_task(
                file_path=str(test_file),
                task_instructions="Write a function called add(a, b) that returns the sum of two numbers.",
                context_files=[]
            )
            print(f"\n[Delegation Result] {result}")
            self.assertTrue(test_file.exists())
            content = test_file.read_text(encoding="utf-8")
            self.assertIn("def add", content)
            self.assertNotIn("```", content)
        finally:
            if test_file.exists():
                test_file.unlink()


if __name__ == "__main__":
    unittest.main()
