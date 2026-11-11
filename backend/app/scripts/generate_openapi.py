from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(__file__).resolve().parents[2] / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()

