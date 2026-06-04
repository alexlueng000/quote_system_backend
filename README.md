# 新案基础报价系统后端

FastAPI 后端原型，当前使用 MySQL 保存报价、明细、用户、国家和费用规则。

## 运行

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## MySQL

先执行初始化脚本：

```bash
mysql -u root -p < mysql_init.sql
```

后端通过环境变量读取连接信息：

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=quote_system
```

也可以在后端目录创建 `.env` 文件，服务启动时会自动读取。

接口文档：

```text
http://localhost:8000/docs
```

## 当前 API

- `GET /health`
- `GET /api/v1/bootstrap`
- `POST /api/v1/quotations/generate`
- `POST /api/v1/quotations`
- `GET /api/v1/quotations`
- `GET /api/v1/quotations/{quotation_id}`
- `PATCH /api/v1/quotations/{quotation_id}/status`
- `GET /api/v1/quotations/{quotation_id}/export`
- `GET /api/v1/statistics`
