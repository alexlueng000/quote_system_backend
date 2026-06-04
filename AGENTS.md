# AGENTS.md — FastAPI Backend

> Codex 启动时自动读取。  
> 本项目以稳定、清晰、可维护为优先级，不追求过度设计，不随意引入复杂方案。

---

## 1. 项目结构

```text
/
├── app/
│   ├── api/             # 路由层，只处理请求和响应
│   ├── core/            # 配置、日志、安全
│   ├── models/          # SQLAlchemy ORM 模型
│   ├── schemas/         # Pydantic 请求/响应模型
│   ├── crud/            # 数据库基础操作
│   ├── services/        # 业务逻辑
│   ├── db/              # 数据库连接与 Session
│   ├── utils/           # 通用工具函数
│   └── main.py          # FastAPI 入口
├── alembic/             # 数据库迁移
├── tests/               # 测试
├── scripts/             # 初始化或维护脚本
├── docs/                # 项目文档
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md
```

**核心规则：**

- `app/api/` 只写路由，不写复杂业务逻辑。
- 业务逻辑放在 `app/services/`。
- 数据库操作放在 `app/crud/`。
- ORM 模型放在 `app/models/`。
- 请求和响应结构放在 `app/schemas/`。
- 配置、日志、安全相关代码放在 `app/core/`。

---

## 2. 运行项目

```bash
# 创建虚拟环境
python -m venv .venv

# Windows 激活
.venv\Scripts\activate

# macOS / Linux 激活
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

接口文档地址：

```text
http://localhost:8000/docs
```

如项目使用 Docker：

```bash
docker compose up -d --build
```

---

## 3. 前置条件

- Python 3.12+
- PostgreSQL 16+
- `.env` 已根据 `.env.example` 配置
- 如使用 Redis、Celery、对象存储等，必须在 `.env.example` 中保留示例配置

禁止提交真实 `.env` 文件。

---

## 4. 数据库迁移

项目使用 Alembic 管理数据库迁移。

```bash
# 生成迁移文件
alembic revision --autogenerate -m "add_xxx"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

**规则：**

- 修改数据库结构必须生成 migration。
- 禁止只改 ORM Model 不生成迁移。
- 禁止直接手动改生产数据库。
- 删除字段、修改字段类型、删除表时，必须说明风险和回滚方式。

---

## 5. 检查与测试

常用命令：

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

完整验证命令：

```bash
ruff check . && ruff format --check . && mypy app && pytest
```

任务完成前，必须尽量跑完整验证。

如未运行测试，必须明确说明原因，不能假装已验证。

---

## 6. 编码规范

### 命名

- 变量 / 函数：`snake_case`
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- 文件名：`snake_case.py`
- 数据库表名：`snake_case`
- API 路径：小写短横线，例如 `/user-profiles`

### Type Hint

- 所有函数必须写参数类型和返回类型。
- 禁止滥用 `Any`。
- 禁止使用裸 `dict`、`list`、`tuple`，要写清楚内部类型。
- 数据库查询返回值必须显式标注。

示例：

```python
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    ...
```

不要写：

```python
async def get_user_by_id(db, user_id):
    ...
```

---

## 7. 分层规则

### API 层

只负责：

- 接收请求
- 参数校验
- 权限依赖
- 调用 service
- 返回响应

禁止在 API 路由中：

- 写复杂业务逻辑
- 直接操作数据库
- 拼复杂 SQL
- 处理复杂第三方流程

### Service 层

负责：

- 业务规则
- 流程编排
- 状态判断
- 调用 crud
- 调用第三方服务

### CRUD 层

负责：

- 查询数据库
- 新增、更新、删除
- 封装可复用数据库操作

不负责业务判断。

---

## 8. API 规范

推荐 REST 风格：

```text
GET    /api/v1/users
GET    /api/v1/users/{user_id}
POST   /api/v1/users
PATCH  /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
```

响应结构应尽量统一。

单个资源：

```json
{
  "data": {},
  "message": "success"
}
```

列表资源：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

错误响应：

```json
{
  "detail": {
    "code": "USER_NOT_FOUND",
    "message": "User not found"
  }
}
```

---

## 9. 异常与日志

- 业务异常应统一封装，不要到处直接抛 `HTTPException`。
- 日志统一使用项目 logger。
- 禁止使用 `print()` 调试。
- 禁止记录密码、token、secret、身份证号、银行卡号等敏感信息。
- 第三方接口失败时，应记录必要上下文和错误原因。

---

## 10. 安全规则

- 密码必须加密存储，禁止明文保存。
- JWT secret、数据库密码、API key 必须从环境变量读取。
- 禁止硬编码密钥。
- 需要登录的接口必须加认证。
- 管理员接口必须加权限校验。
- 文件上传必须校验类型、大小和扩展名。
- 外部输入不能直接拼接 SQL。

---

## 11. 依赖管理

禁止随意引入新依赖。

新增依赖前必须判断：

- 是否真的需要
- 是否可以用已有依赖或标准库解决
- 是否影响镜像体积
- 是否有安全风险
- 是否维护活跃

新增依赖后必须更新依赖配置文件。

---

## 12. 测试要求

必须写测试的情况：

- 新增 API
- 新增 service 逻辑
- 新增权限判断
- 新增数据库查询逻辑
- 修复 bug
- 修改核心业务流程

测试要求：

- 单元测试覆盖核心逻辑。
- API 测试覆盖正常路径和主要异常路径。
- 数据库测试必须使用测试数据库。
- 不允许为了通过测试删除关键断言。

---

## 13. Git 规范

### 分支

```text
feature/xxx
fix/xxx
chore/xxx
refactor/xxx
```

### Commit

使用 Conventional Commits：

```text
feat: add user login api
fix: correct token expiration logic
chore: update docker config
refactor: split user service
test: add user tests
```

### PR 要求

PR 描述必须说明：

- 改了什么
- 为什么改
- 怎么验证
- 是否涉及数据库迁移
- 是否影响已有 API
- 是否有风险

改动超过 200 行，优先拆分。

数据库迁移尽量单独 PR。

---

## 14. 禁止项

- 禁止在路由里堆业务逻辑。
- 禁止在路由里直接写复杂数据库查询。
- 禁止提交 `.env`。
- 禁止硬编码密码、token、API key。
- 禁止使用 `print()` 调试。
- 禁止随意引入新依赖。
- 禁止无 migration 修改数据库结构。
- 禁止把 ORM Model 直接作为 API response。
- 禁止为了通过测试删除断言。
- 禁止无关重构。
- 禁止删除或修改 `docs/` 下文件，除非任务明确要求。

---

## 15. 完成标准

任务完成必须满足：

- 代码符合当前需求，没有额外发挥。
- 结构分层清晰。
- 类型标注完整。
- 错误响应结构一致。
- 涉及数据库时有 migration。
- 涉及新接口时有测试。
- lint / typecheck / test 尽量通过。
- 没有无关文件改动。
- 没有残留调试代码。
- 没有硬编码敏感信息。

---

## 16. Codex 自检流程

修改完成后按顺序检查：

1. 是否只实现当前任务。
2. 代码是否放在正确目录。
3. 函数是否有类型标注。
4. 是否有不该出现的业务逻辑堆在 API 层。
5. 数据库变更是否有 migration。
6. 核心逻辑是否有测试。
7. 是否运行验证命令。
8. diff 是否只包含必要改动。
9. 是否删除临时日志和调试代码。
10. 是否说明完成内容、验证方式和风险。

---

## 17. 默认技术栈

如任务没有特别说明，默认使用：

- FastAPI
- Python 3.12+
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pydantic v2
- Pytest
- Ruff
- MyPy
- Docker Compose

不要主动替换技术栈。

---

## 18. 输出格式

Codex 完成任务后，应按以下格式回复：

```text
完成内容：
- ...

验证方式：
- ...

风险 / 注意事项：
- ...
```

如果没有运行测试，必须写明：

```text
未运行测试，原因是：...
```

不能假装已经运行过测试。