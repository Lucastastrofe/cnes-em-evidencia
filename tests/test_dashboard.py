import ast
import json
import unittest
from pathlib import Path


class DashboardContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[1]
        cls.source = (cls.root / "streamlit_app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.public_data = json.dumps(
            [
                json.loads(
                    (cls.root / "data" / "published" / "dashboard.json").read_text(
                        encoding="utf-8"
                    )
                ),
                json.loads(
                    (cls.root / "data" / "published" / "audit-report.json").read_text(
                        encoding="utf-8"
                    )
                ),
            ]
        ).lower()

    def test_entrypoint_is_a_single_streamlit_dashboard(self):
        calls = {
            node.func.attr
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("set_page_config", calls)
        self.assertIn("metric", calls)
        self.assertIn("bar_chart", calls)
        self.assertIn("dataframe", calls)
        self.assertIn("selectbox", calls)

    def test_static_site_was_removed(self):
        self.assertFalse((self.root / "site" / "index.html").exists())

    def test_published_data_excludes_source_columns_outside_the_contract(self):
        for prohibited in (
            "nu_telefone",
            "no_email",
            "no_logradouro",
            "nu_endereco",
            "no_bairro",
            "co_cep",
            "nu_cnpj",
            "nu_latitude",
            "nu_longitude",
            "no_razao_social",
            "no_fantasia",
        ):
            self.assertNotIn(prohibited, self.public_data)


if __name__ == "__main__":
    unittest.main()
