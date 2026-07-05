import os
import subprocess
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec, stable_text_embedding


async def _sample_tool(query: str):
    return {"query": query}


class TestRuntimeStack(unittest.TestCase):
    def test_stable_text_embedding_is_process_stable(self):
        code = (
            "from core_runtime.runtime_stack import stable_text_embedding; "
            "print(stable_text_embedding('query_db', 8).tolist())"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = PROJECT_ROOT
        first = subprocess.check_output([sys.executable, "-c", code], cwd=PROJECT_ROOT, env=env, text=True)
        second = subprocess.check_output([sys.executable, "-c", code], cwd=PROJECT_ROOT, env=env, text=True)
        self.assertEqual(first, second)
        np.testing.assert_allclose(stable_text_embedding("query_db", 8), stable_text_embedding("query_db", 8))

    def test_physical_tool_registry_exposes_configured_metadata(self):
        registry = PhysicalToolRegistry(
            [
                ToolSpec(
                    name="sample_query",
                    handler=_sample_tool,
                    capabilities={"read", "query"},
                    criticality_score=0.2,
                )
            ]
        )

        self.assertEqual(registry.get_tool_names(), ["sample_query"])
        self.assertIs(registry.get_handler("sample_query"), _sample_tool)
        self.assertEqual(registry.as_capability_map()["sample_query"], {"read", "query"})
        self.assertEqual(registry.as_criticality_map()["sample_query"], 0.2)
        self.assertIsNone(registry.get_handler("missing_tool"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
