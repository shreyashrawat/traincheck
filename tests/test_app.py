"""Streamlit app test via AppTest (no server needed).

Run from the project root with the venv Python:
    .venv/bin/python tests/test_app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest  # noqa: E402


def main():
    root = Path(__file__).resolve().parent.parent
    at = AppTest.from_file(str(root / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    sample = (root / "samples" / "sample_policy.txt").read_text(encoding="utf-8")
    at.text_area(key="policy_text").set_value(sample).run()
    at.button(key="audit").click().run()
    assert not at.exception, at.exception
    texts = [str(m.value) for m in at.markdown] + [str(s.value) for s in at.success]
    assert any("8.6" in t for t in texts), texts
    assert any("Clear" in t for t in texts), texts
    print("app test passed: hero shows 8.6 / Clear")


if __name__ == "__main__":
    main()
