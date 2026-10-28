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
    successes = [str(s.value) for s in at.success]
    assert any("14/16" in s for s in successes), successes
    print("app test passed:", successes)


if __name__ == "__main__":
    main()
