import unittest
from unittest.mock import patch

from cnes_audit.api_client import fetch_catalog, fetch_table


class ApiClientTest(unittest.TestCase):
    def test_remote_table_uses_selected_partition(self):
        payload = {"metadados": {"id_execucao": "test"}, "total": 1, "dados": [{"uf": "SP"}]}
        with patch("cnes_audit.api_client.fetch_json", return_value=payload) as fetch:
            self.assertEqual(fetch_table("fonte_leitos", "SP"), payload)
            fetch.assert_called_once_with("tabelas/fonte_leitos/ufs/SP.json")

    def test_unexpected_remote_shape_is_rejected(self):
        with patch("cnes_audit.api_client.fetch_json", return_value={"tabelas": [{"tabela": "valid", "linhas": 1, "colunas": 2}]}):
            with self.assertRaises(ValueError):
                fetch_catalog()
        with patch("cnes_audit.api_client.fetch_json", return_value={"dados": [{}], "total": 10}):
            with self.assertRaises(ValueError):
                fetch_table("valid")

    def test_arbitrary_paths_are_not_accepted(self):
        with self.assertRaises(ValueError):
            fetch_table("../outside")
