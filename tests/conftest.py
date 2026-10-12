"""pytest 공통 설정 — 프로젝트 루트를 sys.path 에 추가해 `import backend` 가 되게 합니다."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
