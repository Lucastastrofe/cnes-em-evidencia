import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class StudyNavigationTest(unittest.TestCase):
    def test_study_shows_one_topic_and_opens_profile_on_demand(self):
        app = AppTest.from_file(Path(__file__).parents[1] / "streamlit_app.py").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertEqual(next(item for item in app.selectbox if item.label == "O que você quer investigar?").value, "Mapa e perfis")
        self.assertEqual(next(item for item in app.radio if item.label == "Visualização").value, "Mapa")
        self.assertFalse(any(item.label == "Buscar tipo de equipe" for item in app.text_input))
        next(item for item in app.button if item.label == "Detalhar esta UF").click().run(timeout=40)
        self.assertFalse(app.exception)
        self.assertEqual(next(item for item in app.radio if item.label == "Visualização").value, "Perfil da UF")
        self.assertTrue(any(item.label == "Buscar tipo de equipe" for item in app.text_input))
        self.assertFalse(any(item.label == "O que comparar" for item in app.selectbox))
        self.assertFalse(any(item.label == "Forma de comparação" for item in app.radio))
        next(item for item in app.selectbox if item.label == "O que você quer investigar?").select("Profissionais").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertTrue(any(item.value == "Profissionais e atendimento ao SUS" for item in app.title))
        self.assertFalse(any(item.label == "Visualização" for item in app.radio))

    def test_state_is_preserved_between_map_profile_and_method(self):
        app = AppTest.from_file(Path(__file__).parents[1] / "streamlit_app.py").run(timeout=40)
        next(item for item in app.selectbox if item.label == "Estado para explorar").select("São Paulo").run(timeout=40)
        next(item for item in app.button if item.label == "Detalhar esta UF").click().run(timeout=40)
        self.assertEqual(app.selectbox(key="territory_state").value, "São Paulo")
        self.assertTrue(any(item.value == "Leitos cadastrados em São Paulo" for item in app.subheader))
        app.radio(key="territory_view").set_value("Como interpretar").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertTrue(any(item.value == "Antes de comparar os números" for item in app.subheader))
        self.assertFalse(any(item.label == "O que comparar" for item in app.selectbox))
        self.assertFalse(app.metric)
        app.radio(key="territory_view").set_value("Mapa").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="territory_state").value, "São Paulo")

    def test_map_callback_reselects_previous_state_and_ignores_empty_event(self):
        from unittest.mock import patch
        from streamlit_app import sync_territory_selection
        state = {"territory_map": {"selection": {"uf": [{"code": "35"}]}}, "territory_state": "Acre"}
        with patch("streamlit_app.st.session_state", state):
            sync_territory_selection({"35": "São Paulo"})
            self.assertEqual(state["territory_state"], "São Paulo")
            state["territory_state"] = "Acre"
            sync_territory_selection({"35": "São Paulo"})
            self.assertEqual(state["territory_state"], "São Paulo")
            state["territory_map"] = {"selection": {"uf": []}}
            sync_territory_selection({"35": "São Paulo"})
            self.assertEqual(state["territory_state"], "São Paulo")
