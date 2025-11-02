# FastAPI Vue3 Admin - Backend

一个基于 FastAPI 的现代化后端管理系统，为前端 Vue3 管理系统提供完整的 API 服务支持。

## 🚀 项目特性

- **现代技术栈**: FastAPI + SQLAlchemy 2.0 + Pydantic 2.x
- **多数据库支持**: MySQL、PostgreSQL、SQLite
- **异步架构**: 支持高并发异步数据库操作
- **权限管理**: 完整的 RBAC 权限控制体系
- **任务调度**: 基于 APScheduler 的定时任务系统
- **日志监控**: 完整的操作日志和系统监控
- **代码生成**: 智能化代码生成工具
- **AI 集成**: 支持 OpenAI 大模型调用
- **云存储**: 支持阿里云 OSS 对象存储

## 🏗️ 系统架构

### 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| FastAPI | 0.115.2 | 现代 Web 框架 |
| SQLAlchemy | 2.0.36 | ORM 框架 |
| Alembic | 1.15.1 | 数据库迁移工具 |
| Pydantic | 2.x | 数据验证与序列化 |
| APScheduler | 3.11.0 | 定时任务调度 |
| Redis | 5.2.1 | 缓存与会话存储 |
| Uvicorn | 0.30.6 | ASGI 服务器 |
| Python | 3.10+ | 运行环境 |

### 架构设计

```txt
📦 分层架构 (MVC)
├── 🎯 Controller   # 控制器层 - 处理HTTP请求
├── 🏢 Service      # 业务层 - 核心业务逻辑
├── 💾 CRUD         # 数据访问层 - 数据库操作
└── 📊 Model        # 模型层 - 数据模型定义
```

## 📁 项目结构

```txt
fastapi_vue3_admin/backend/
├── 📁 app/                     # 项目核心代码
│   ├── 💾 alembic/             # 数据库迁移管理
│   ├── 🌐 api/                 # API 接口模块
│   │   └── v1/               # API v1 版本
│   │       ├── module_system/  # 系统管理模块
│   │       ├── module_monitor/ # 系统监控模块
│   │       ├── module_ai/      # AI 功能模块
│   │       └── module_*/       # 其他业务模块
│   ├── 📄 common/              # 公共组件（常量、枚举、响应封装）
│   ├── ⚙️ config/              # 项目配置文件
│   ├── 💖 core/                # 核心模块（数据库、中间件、安全）
│   ├── ⏰ module_task/         # 定时任务模块
│   ├── 🔌 plugin/              # 插件模块
│   ├── 📜 scripts/             # 初始化脚本和数据
│   └── 🛠️ utils/               # 工具类（验证码、文件上传等）
├── 🌍 env/                     # 环境配置文件
├── 📄 logs/                    # 日志输出目录
├── 📊 sql/                     # SQL 初始化脚本
├── 📷 static/                  # 静态资源文件
├── 🚀 main.py                  # 项目启动入口
├── 📄 alembic.ini              # Alembic 迁移配置
├── 📎 requirements.txt         # Python 依赖包
└── 📝 README.md                # 项目说明文档
```

### 模块设计

每个业务模块采用统一的分层结构：

```txt
module_*/
├── controller.py    # 控制器 - HTTP 请求处理
├── service.py       # 服务层 - 业务逻辑处理
├── crud.py          # 数据层 - 数据库操作
├── model.py         # ORM 模型 - 数据库表定义
├── schema.py        # Pydantic 模型 - 数据验证
└── param.py         # 参数模型 - 请求参数
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.10+
- **数据库**: MySQL 8.0+ / PostgreSQL 13+ / SQLite 3.x
- **Redis**: 6.0+ (可选)

### 安装与运行

#### 1. 项目初始化

```bash
# 克隆项目
git clone <repository-url>
cd fastapi_vue3_admin/backend

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip3 install -r requirements.txt
```

#### 2. 环境配置

复制并编辑环境配置文件：

```bash
cp env/dev.env.example env/dev.env
# 编辑 env/dev.env 文件，配置数据库连接和其他参数
```

主要配置项：

- `DATABASE_URL`: 数据库连接地址
- `SECRET_KEY`: JWT 加密密钥
- `REDIS_URL`: Redis 连接地址（可选）

#### 3. 数据库初始化

```bash
# 生成迁移文件（仅首次或模型变更时）
python main.py revision "数据迁移" --env=dev(不加默认为dev)

# 应用数据库迁移
python main.py upgrade --env=dev(不加默认为dev)
```

#### 4. 启动服务

```bash
# 开发环境启动
python main.py run --env=dev (不加默认为dev)

# 生产环境启动
python main.py run --env=prod (不加默认为dev)

# 或使用 uvicorn 直接启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务成功启动后，您可以访问：

- **API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **替代文档**: [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)
- **健康检查**: [http://localhost:8000/health](http://localhost:8000/health)

## 📚 API 文档

### 主要接口模块

| 模块 | 路径 | 说明 |
|------|------|------|
| 用户管理 | `/api/v1/system/user` | 用户增删改查、角色分配 |
| 角色管理 | `/api/v1/system/role` | 角色管理、权限分配 |
| 菜单管理 | `/api/v1/system/menu` | 系统菜单、权限节点 |
| 部门管理 | `/api/v1/system/dept` | 组织架构管理 |
| 岗位管理 | `/api/v1/system/position` | 岗位信息管理 |
| 系统监控 | `/api/v1/monitor/*` | 系统性能、日志监控 |
| 任务调度 | `/api/v1/monitor/job` | 定时任务管理 |
| 文件管理 | `/api/v1/common/file` | 文件上传下载 |
| 代码生成 | `/api/v1/generator/*` | 代码生成工具 |

### 认证授权

系统使用 JWT Bearer Token 进行身份验证：

```bash
# 登录获取 Token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "123456"}'

# 使用 Token 访问受保护的资源
curl -X GET "http://localhost:8000/api/v1/system/user/list" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🛠️ 开发指南

### 项目配置

主要配置文件位于 `app/config/setting.py`，支持通过环境变量进行覆盖。

### 数据库迁移

```bash
# 查看当前迁移状态
python3 main.py current --env=dev

# 查看迁移历史
python3 main.py history --env=dev

# 回滚到上一个版本
python3 main.py downgrade -1 --env=dev
```

### 添加新模块

1. 在 `app/api/v1/` 下创建新的模块目录
2. 按照现有模块结构创建文件：
   - `model.py` - SQLAlchemy ORM 模型
   - `schema.py` - Pydantic 数据模型
   - `crud.py` - 数据库操作层
   - `service.py` - 业务逻辑层
   - `controller.py` - API 控制器
   - `param.py` - 请求参数模型
3. 在主路由中注册新模块

### 测试

```bash
# 运行单元测试
pytest tests/

# 运行指定测试文件
pytest tests/test_user.py -v

# 生成测试覆盖率报告
pytest --cov=app tests/
```

## 📊 监控与日志

### 日志级别

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息（默认级别）
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

### 性能监控

系统内置了完整的性能监控功能：

- API 响应时间监控
- 数据库连接池监控
- 内存与 CPU 使用率监控
- 自定义业务指标监控

## 🚀 部署指南

### Docker 部署

```bash
# 构建镜像
docker build -t fastapi-admin .

# 运行容器
docker run -d \
  --name fastapi-admin \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  fastapi-admin
```

### 传统部署

```bash
# 使用 Gunicorn 作为 WSGI 服务器
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

### 代码规范

- 遵循 PEP 8 Python 编码规范
- 使用类型注解 (Type Hints)
- 编写单元测试
- 添加必要的注释和文档

## 📝 更新日志

### v1.0.0 (2024-09-06)

- ✨ 初始版本发布
- ✨ 完整的用户权限管理系统
- ✨ 支持多数据库类型
- ✨ 定时任务调度功能
- ✨ 代码生成工具
- ✨ AI 集成功能

## 📜 相关链接

- **FastAPI 官方文档**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **SQLAlchemy 文档**: [https://docs.sqlalchemy.org/](https://docs.sqlalchemy.org/)
- **Pydantic 文档**: [https://pydantic-docs.helpmanual.io/](https://pydantic-docs.helpmanual.io/)

## 💬 支持与反馈

如果您在使用过程中遇到问题或有任何建议，请通过以下方式联系我们：

- 🐛 **Bug 报告**: 请在 GitHub Issues 中提交
- 💡 **功能建议**: 请在 GitHub Discussions 中讨论
- 💬 **技术交流**: 欢迎参与项目讨论

---

❤️ **感谢您的关注和支持！** 如果这个项目对您有帮助，请给我们一个 ⭐️ Star！


# MCP 模块

## 概述

MCP (Model Context Protocol) 模块为系统提供与AI模型交互的能力，基于FastAPI-MCP实现。

## 功能特性

- 智能对话接口
- 流式和非流式响应支持
- WebSocket聊天支持
- MCP服务器状态监控

## API接口

### 智能对话

```
POST /api/v1/mcp/chat
```

请求参数：
- `message` (string, required): 聊天消息
- `stream` (boolean, optional): 是否流式返回，默认为false

### 获取服务器状态

```
GET /api/v1/mcp/status
```

### WebSocket聊天

```
GET /api/v1/mcp/ws/chat
```

## MCP集成

系统已集成FastAPI-MCP，可通过以下URL访问MCP服务器：

```
http://localhost:8000/mcp
```

## 配置

在系统配置中设置以下参数：

- `OPENAI_API_KEY`: OpenAI API密钥
- `OPENAI_BASE_URL`: OpenAI API基础URL
- `OPENAI_MODEL`: OpenAI模型名称
