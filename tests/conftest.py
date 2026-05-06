import os
import sys
from pathlib import Path

# 1) 把项目根目录加入 sys.path，确保能 import app.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2) 尝试加载项目根目录的 .env（如果你有的话）
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

# 3) 给测试环境兜底必要环境变量（避免 pydantic Settings 初始化失败）
#    如果你的 .env 已经有值，这里不会覆盖（setdefault）
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/store_locator")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")
