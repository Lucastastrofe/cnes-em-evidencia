import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class StudyNavigationTest(unittest.TestCase):
    def test_study_shows_one_topic_and_opens_profile_on_demand(self):
        app = AppTest.from_file(Path(__file__).parents[1] / "streamlit_app.py").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertEqual(next(item for item in app.selectbox if item.label == "Tema da análise").value, "Mapa e perfis")
        self.assertEqual(next(item for item in app.radio if item.label == "Visualização").value, "Mapa")
        self.assertFalse(any(item.label == "Buscar tipo de equipe" for item in app.text_input))
        next(item for item in app.button if item.label == "Detalhar esta UF").click().run(timeout=40)
        self.assertFalse(app.exception)
        self.assertEqual(next(item for item in app.radio if item.label == "Visualização").value, "Perfil da UF")
        self.assertTrue(any(item.label == "Buscar tipo de equipe" for item in app.text_input))
        next(item for item in app.selectbox if item.label == "Tema da análise").select("Profissionais").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertTrue(any(item.value == "Profissionais e atendimento ao SUS" for item in app.title))
        self.assertFalse(any(item.label == "Visualização" for item in app.radio))
