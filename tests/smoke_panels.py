"""Manual release smoke check: run with python tests/smoke_panels.py."""
from streamlit.testing.v1 import AppTest


panels = ["quality", "population", "bed", "team", "service", "bed_history", "professional", "integrated"]
functions = [f"render_{panel}_panel" for panel in panels] + ["render_data_center"]
for function in functions:
    source = (
        "import runpy\n"
        "namespace = runpy.run_path('streamlit_app.py', run_name='smoke')\n"
        "dashboard, audit = namespace['load_data'](namespace['published_data_version']())\n"
        f"namespace['{function}'](dashboard, audit)\n"
    )
    app = AppTest.from_string(source).run(timeout=40)
    if app.exception:
        raise RuntimeError(f"{function}: {list(app.exception)}")
    print(f"OK: {function}")
