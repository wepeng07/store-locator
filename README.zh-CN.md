# Store Locator Service

英文版默认说明： [README.md](README.md)

Store Locator Service 是一个基于 FastAPI 的门店定位后端服务，支持门店搜索、权限化后台管理，以及 CSV 批量导入。

## 项目价值

- 帮助用户更快找到最近且符合条件的门店，提升到店与转化效率。
- 支持 `pickup`、`returns`、`pharmacy` 等服务筛选，适配全渠道零售场景。
- 通过后台 CRUD、批量导入和 RBAC，降低门店数据维护成本。
- 为后续门店分析、区域运营和服务能力扩展提供基础平台。

## 核心功能

- 支持按地址、邮编、经纬度搜索门店
- 支持半径、服务类型、门店类型、营业中筛选
- 支持公开搜索接口缓存与限流
- 支持 JWT 登录、刷新、登出与角色权限控制
- 支持后台门店 CRUD 与可选自动地理编码
- 支持 CSV 批量导入、校验与整批回滚
- 支持 Alembic 迁移、种子脚本和端到端测试

## 技术栈

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic Settings
- HTTPX

## 项目结构

```text
app/
  api/routes/         HTTP 接口
  core/               配置、鉴权、JWT、RBAC
  db/                 数据库引擎与依赖
  middlewares/        中间件
  models/             SQLAlchemy 模型
  services/           搜索、地理编码、缓存
  utils/              地理与业务工具函数
alembic/              数据库迁移
scripts/              本地种子与检查脚本
tests/                端到端测试
docs/                 额外文档
```

## 快速开始

1. 创建虚拟环境并安装依赖：

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. 复制环境变量模板：

   ```bash
   cp .env.example .env
   ```

3. 启动 PostgreSQL：

   ```bash
   docker compose up -d db
   ```

4. 执行迁移并导入种子数据：

   ```bash
   alembic upgrade head
   python scripts/seed.py
   python scripts/seed_services.py
   python scripts/seed_users.py
   ```

5. 启动服务：

   ```bash
   uvicorn app.main:app --reload
   ```

6. 运行测试：

   ```bash
   pytest
   ```

## 主要接口

- `POST /api/stores/search`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/admin/ping`
- `POST /api/admin/stores`
- `GET /api/admin/stores`
- `GET /api/admin/stores/{store_id}`
- `PATCH /api/admin/stores/{store_id}`
- `DELETE /api/admin/stores/{store_id}`
- `POST /api/admin/stores/import`

## 说明

- `requirement.txt` 仅用于兼容，实际依赖入口是 `requirements.txt`。
