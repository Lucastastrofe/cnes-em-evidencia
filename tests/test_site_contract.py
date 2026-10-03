import json
import unittest
from pathlib import Path


class SiteContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1] / "site"
        cls.html = (root / "index.html").read_text(encoding="utf-8")
        cls.javascript = (root / "app.js").read_text(encoding="utf-8")
        cls.public_data = json.dumps(
            [
                json.loads((root / "data" / "dashboard.json").read_text(encoding="utf-8")),
                json.loads((root / "data" / "audit-report.json").read_text(encoding="utf-8")),
            ]
        ).lower()

    def test_page_has_accessible_structure_and_runtime_states(self):
        self.assertIn('<main id="conteudo">', self.html)
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('id="loading" role="status"', self.html)
        self.assertIn('id="error" role="alert"', self.html)
        self.assertIn('<label for="state-filter">', self.html)
        self.assertIn('aria-live="polite"', self.html)

    def test_runtime_uses_text_content_for_source_data(self):
        self.assertIn("textContent", self.javascript)
        self.assertNotIn("innerHTML", self.javascript)

    def test_copy_does_not_claim_healthcare_quality(self):
        self.assertIn("não a qualidade do atendimento", self.html)

    def test_published_snapshot_excludes_source_columns_outside_the_contract(self):
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
