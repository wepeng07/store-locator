# Store Locator 仓库审计与首发计划

## 1. 当前仓库状态

- 本地目录已经是 Git 仓库。
- 已绑定 GitHub 远端：`https://github.com/wepeng07/store-locator.git`
- 远端仓库当前为空，没有默认分支，也没有历史提交。
- 本地项目代码大部分仍处于未跟踪状态，说明代码尚未完成首传。

这个状态适合按真实开发流程重建首批提交历史，而不是一次性把所有文件推上去。

## 2. 项目结构检查

```text
app/
  api/routes/
    stores.py          公开门店搜索
    auth.py            登录、刷新、登出
    admin_ping.py      RBAC 探针接口
    admin_stores.py    后台门店 CRUD
    admin_import.py    CSV 批量导入
  core/
    config.py          环境配置
    auth_deps.py       Token 解析依赖
    jwt_utils.py       JWT 生成与校验
    passwords.py       密码哈希
    rbac.py            角色权限控制
  db/
    base.py            SQLAlchemy Base
    session.py         Engine / Session
    deps.py            FastAPI DB 依赖
  middlewares/
    rate_limit.py      public search 限流
  models/
    store.py           门店模型
    service.py         服务模型
    store_service.py   门店与服务关联
    user.py            用户模型
    refresh_token.py   Refresh Token 模型
  services/
    store_search.py    地理搜索逻辑
    geocoding.py       地址/邮编转坐标
    search_cache.py    搜索缓存
    store_services.py  门店服务聚合
  utils/
    geo.py             bounding box 计算
    open_now.py        营业时间判定
alembic/
  versions/            数据库迁移脚本
scripts/
  seed.py              门店种子数据
  seed_services.py     服务种子数据
  seed_users.py        用户种子数据
tests/
  test_e2e.py          端到端接口测试
```

## 3. 已具备的业务能力

### 公开能力

- 支持通过地址、邮编、经纬度搜索门店
- 支持半径、服务、门店类型、营业中筛选
- 支持响应缓存与搜索限流

### 内部运营能力

- 支持门店列表、详情、创建、更新、停用
- 支持 CSV 批量导入和整批回滚
- 支持地址自动地理编码

### 安全与平台能力

- 支持 JWT 登录、刷新、登出
- 支持 admin / marketer / viewer 三类角色权限
- 支持数据库迁移、种子脚本、健康检查

## 4. 商业价值

### 4.1 提升门店转化率

消费者能更快找到最近、仍在营业、且具备所需服务的门店，这直接影响到到店率、履约率和转化率。

### 4.2 支撑全渠道零售

当门店搜索可按 `pickup`、`returns`、`pharmacy` 等能力筛选时，它就不仅是 locator，而是全渠道履约入口。

### 4.3 降低运营维护成本

管理员和运营角色可以通过后台 API 或 CSV 批量维护门店，减少人工录入和重复校对工作。

### 4.4 提高组织治理能力

通过 RBAC 将读、写、管理职责拆开后，企业可以安全地把门店数据维护下放给业务团队，而不必暴露数据库权限。

### 4.5 具备平台化扩展潜力

现有模型已经适合继续扩展库存、促销、服务 SLA、商圈分析、区域报表等能力，具备演化为门店运营平台的基础。

## 5. 建议的 GitHub 首发顺序

1. `chore: bootstrap store locator backend`
   - GitHub 基础治理文件
   - 环境配置、数据库连接、Alembic、基础模型
   - 健康检查与本地运行说明

2. `feat: add public store search API`
   - 公开搜索接口
   - 地理搜索、缓存、限流、营业状态判定

3. `feat: add authentication and role-based access control`
   - 用户模型、refresh token、JWT、RBAC
   - 登录/刷新/登出与权限探针

4. `feat: add admin store management endpoints`
   - 后台门店 CRUD
   - 门店服务绑定与可选自动 geocoding

5. `feat: add CSV store import workflow`
   - CSV 校验、批量导入、失败回滚
   - 示例 CSV 数据文件

6. `test: add end-to-end coverage and seed scripts`
   - 测试、种子脚本、补充说明

这个顺序能让提交历史既符合开发节奏，也能让每一批提交在 GitHub 上具备清晰的业务含义。

