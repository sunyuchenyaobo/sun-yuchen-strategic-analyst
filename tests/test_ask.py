# -*- coding: utf-8 -*-
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ask", ROOT / "ask.py")
ask = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ask)


class AgentReadySearchTests(unittest.TestCase):
    def test_scenario_labels_are_attached_to_l1_atoms(self):
        entries = ask.load_corpus()
        atom = next(e for e in entries if e.get("id") == "L1-SYC-001")
        self.assertIn("时代与宏观", atom["scenarios"])

    def test_json_output_separates_summary_from_verbatim_quote(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "ask.py"), "借钱创业", "--top", "3", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["query"], "借钱创业")
        self.assertTrue(payload["results"])
        l1 = next(item for item in payload["results"] if item["kind"] == "L1原子")
        self.assertTrue(l1["summary"])
        self.assertTrue(l1["quote"])
        self.assertEqual(l1["source_period"], "2016-2017")
        self.assertNotEqual(l1["summary"], l1["quote"])

    def test_interview_results_keep_their_own_year(self):
        results = ask.search_corpus("Blue Origin 太空酒店", top=10)
        interview = next(item for item in results if item["kind"] == "访谈")
        self.assertEqual(interview["source_period"], "2026")

    def test_unrelated_query_returns_no_results(self):
        results = ask.search_corpus("zzzxxyyqqq", top=6)
        self.assertEqual(results, [])

    def test_l1_only_returns_only_atoms(self):
        results = ask.search_corpus("原始积累", top=8, l1_only=True)
        self.assertTrue(results)
        self.assertTrue(all(item["kind"] == "L1原子" for item in results))


if __name__ == "__main__":
    unittest.main()
