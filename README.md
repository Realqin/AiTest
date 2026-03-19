# AiTest - AI智能需求分析与测试用例生成系统

## 项目简介

AiTest是一个前后端分离的轻量级项目，基于FastAPI和React实现。项目专注于利用大模型（LLM）进行需求分析、评审和测试用例的自动化生成。

**主要功能：**
- 🎯 项目与需求管理：创建、编辑、删除项目和需求
- 📋 需求导入与预览：支持从Jira、Excel等多种方式导入需求，生成HTML预览
- 🤖 AI需求评审：利用大模型进行多维度需求分析（可测性、可行性、逻辑、清晰度）
- 🧪 测试用例管理：自动生成和手动编辑测试用例，组织成测试模块
- ⚙️ LLM配置管理：支持多个大模型配置（OpenAI、Claude等），智能路由选择最优模型
- 🛠️ 提示词管理：管理和优化各种AI操作的提示词模板
- 🔌 MCP工具集成：支持注册和管理Model Context Protocol工具

**技术栈：**
- 后端：FastAPI, SQLAlchemy, PyMySQL
- 前端：React 18, Vite, Mind Elixir（思维导图）
- 数据库：MySQL 8.4
- 部署：Docker Compose

---

## 完整目录结构与文件说明

```
AiTest/
├── README.md                      # 项目说明文档（本文件）
├── main.py                        # 根目录入口脚本（示例代码）
├── docker-compose.mysql.yml       # MySQL容器编排配置
│
├── backend/                       # 后端应用根目录
│   ├── requirements.txt           # Python依赖列表
│   ├── MYSQL_SCHEMA.md            # 数据库表结构和设计文档
│   │
│   ├── app/                       # FastAPI应用主目录
│   │   ├── __init__.py            # 包初始化文件
│   │   ├── main.py                # FastAPI应用入口，路由注册，中间件配置
│   │   │
│   │   ├── api/                   # API路由模块
│   │   │   ├── __init__.py
│   │   │   ├── agent_config.py    # 智能体角色和提示词配置API（/api/agents）
│   │   │   ├── ai.py              # AI评审、生成、对话API（/api/ai）
│   │   │   ├── llm_config.py      # LLM模型配置管理API（/api/llm-configs）
│   │   │   ├── mcp.py             # MCP工具注册和管理API（/api/mcp）
│   │   │   ├── projects.py        # 项目CRUD和查询API（/api/projects）
│   │   │   ├── prompt_template.py # 提示词模板管理API（/api/prompt-templates）
│   │   │   ├── requirements.py    # 需求CRUD、导入、预览API（/api/requirements）
│   │   │   └── test_cases.py      # 测试用例CRUD和需求映射API（/api/test-cases）
│   │   │
│   │   ├── core/                  # 核心业务逻辑模块
│   │   │   ├── external_access.py # 外部系统访问封装（Jira、URL等）
│   │   │   ├── jira_client.py     # Jira集成客户端，支持问题查询和文档解析
│   │   │   ├── jira_config.py     # Jira账户配置管理
│   │   │   ├── llm_client.py      # LLM API调用客户端，支持流式和异步调用
│   │   │   └── model_router.py    # 智能模型路由，根据条件选择最优LLM配置
│   │   │
│   │   ├── store/                 # 数据存储层
│   │   │   ├── memory_db.py       # 内存数据库封装（数据库CRUD操作，ID生成）
│   │   │   └── requirements/      # 需求文件存储目录
│   │   │
│   │   ├── config/                # 配置文件目录
│   │   │   └── jira_accounts.json # Jira账户配置（JSON格式）
│   │   │
│   │   └── storage/               # 静态资源和上传文件存储
│   │       └── (上传的需求文件存储在此)
│   │
│   ├── sql/                       # 数据库SQL脚本
│   │   └── init/
│   │       └── 001_init_aitest.sql # 数据库初始化脚本（表创建、索引等）
│   │
│   └── vendor/                    # 第三方库和工具
│       ├── bin/                   # 可执行文件
│       ├── cobble/                # 字符串转换工具库（拼写修正）
│       └── mammoth/               # Word文档转HTML转换库
│
└── frontend/                      # 前端应用根目录
    ├── package.json               # npm依赖和脚本配置
    ├── vite.config.js             # Vite构建配置
    ├── index.html                 # HTML入口
    │
    └── src/                       # React源代码
        ├── main.jsx               # React应用入口
        ├── App.jsx                # 主应用组件，模块路由和导航
        ├── api.js                 # 后端API调用封装，所有HTTP请求
        ├── styles.css             # 全局样式
        │
        ├── LlmConfigPage.jsx      # LLM配置页面组件
        ├── PromptManagementPage.jsx    # 提示词模板管理页面
        └── TestCaseWorkflowPage.jsx    # 测试用例管理工作流页面
```

---

## 核心模块详解

### 后端API端点汇总

| 模块 | 端点 | 功能 |
|------|------|------|
| **Projects** | `GET /api/projects` | 分页列表查询（支持关键词搜索） |
| | `POST /api/projects` | 创建新项目 |
| | `PUT /api/projects/{id}` | 更新项目信息 |
| | `DELETE /api/projects/{id}` | 删除项目 |
| **Requirements** | `GET /api/requirements` | 需求列表查询（多维度过滤） |
| | `POST /api/requirements` | 创建需求 |
| | `PUT /api/requirements/{id}` | 更新需求 |
| | `DELETE /api/requirements/{id}` | 删除需求 |
| | `POST /api/requirements/import` | 导入需求（Jira/URL/文件） |
| | `GET /api/requirements/{id}/preview` | 获取需求HTML预览 |
| | `GET /api/requirements/{id}/reviews` | 获取需求评审历史 |
| **AI Review** | `GET /api/ai/checks` | 获取评审检查项列表 |
| | `POST /api/ai/review/start` | 启动需求评审任务 |
| | `GET /api/ai/review/{run_id}/status` | 查询评审运行状态 |
| | `GET /api/ai/review/{run_id}/result` | 获取评审结果 |
| | `POST /api/ai/generate` | 生成内容（测试用例等） |
| | `POST /api/ai/chat` | AI对话接口 |
| **Test Cases** | `GET /api/test-cases` | 测试用例列表 |
| | `POST /api/test-cases` | 创建测试用例 |
| | `PUT /api/test-cases/{id}` | 更新测试用例 |
| | `DELETE /api/test-cases/{id}` | 删除测试用例 |
| | `GET /api/test-case-modules` | 测试模块列表 |
| | `POST /api/test-case-modules` | 创建测试模块 |
| | `PUT /api/test-case-modules/{id}` | 更新模块 |
| | `DELETE /api/test-case-modules/{id}` | 删除模块 |
| **LLM Configs** | `GET /api/llm-configs` | LLM配置列表 |
| | `POST /api/llm-configs` | 创建LLM配置 |
| | `PUT /api/llm-configs/{id}` | 更新配置 |
| | `DELETE /api/llm-configs/{id}` | 删除配置 |
| **Prompts** | `GET /api/prompt-templates` | 提示词模板列表 |
| | `POST /api/prompt-templates` | 创建模板 |
| | `PUT /api/prompt-templates/{id}` | 更新模板 |
| | `DELETE /api/prompt-templates/{id}` | 删除模板 |
| **Agents** | `GET /api/agents` | 智能体角色列表 |
| | `POST /api/agents` | 创建智能体 |
| **MCP** | `GET /api/mcp/tools` | MCP工具列表 |
| | `POST /api/mcp/tools/register` | 注册新工具 |

### 数据库表结构（MySQL）

**关键表说明：**

1. **id_sequences** - 业务ID序列生成器
   - `scope`: 序列范围（如"projects"、"requirements"）
   - `current_value`: 当前值，用于生成递增的业务ID

2. **projects** - 项目表
   - 主要字段：id, name, description, creator
   - 时间戳：created_at, updated_at
   - 扩展字段：extra_data (JSON)

3. **requirements** - 需求表（核心表）
   - 内容字段：title, body_text, summary
   - 状态字段：status, review_status, import_method
   - 文件字段：file_name, stored_file_name, preview_html
   - 预览字段：preview_type, preview_html
   - 评审字段：latest_review_run_id, review_status
   - 索引：project, creator, title, status, import_method

4. **requirement_versions** - 需求版本历史
   - 记录每个需求的版本快照
   - 支持版本回溯和对比

5. **review_runs** - AI评审运行记录
   - 一次评审执行对应一条记录
   - 字段：status(running/completed/failed), progress(0-100), model
   - 关联字段：requirement_id, llm_config_id

6. **test_cases** - 测试用例表
   - 字段：id, project, requirement_id, title, steps, expected_result
   - 组织：module_id（所属测试模块）

7. **llm_configs** - LLM模型配置
   - 支持多个配置记录
   - 字段：provider(openai/claude/qwen等), model, api_key, base_url
   - 参数：temperature, max_tokens, timeout等

8. **prompt_templates** - 提示词模板
   - 字段：name, content, prompt_type(需求评审/用例生成等)
   - 管理：enabled, version, description

### 核心Python模块说明

#### `app/main.py` - FastAPI应用入口
- **功能**：初始化FastAPI应用，注册所有API路由和中间件
- **关键配置**：
  - CORS中间件：允许前端跨域请求
  - OpenAPI文档：路由到 `/swagger` 而非 `/docs`
  - 静态文件挂载：`/assets` 映射到存储目录
- **API标签**：组织8个功能模块的API，生成结构化的Swagger文档

#### `app/store/memory_db.py` - 数据存储层
- **职责**：MySQL数据库的统一访问接口
- **核心类**：`MemoryDB` 类提供字典式API
  - `.new_id(scope)`: 生成新的业务ID
  - `.projects`, `.requirements` 等：表级访问
  - CRUD操作：增删改查封装
- **关键方法**：
  - `clone()`: 深拷贝记录
  - `now_iso()`: 生成ISO格式时间戳

#### `app/core/llm_client.py` - LLM调用客户端
- **功能**：
  - 支持OpenAI兼容的API调用（流式、非流式）
  - JSON对象提取：自动从LLM输出中抽取JSON
  - 异步调用支持
  - 错误重试机制
- **关键函数**：
  - `call_chat_completion()`: 同步调用
  - `call_chat_completion_async()`: 异步调用
  - `extract_json_payload()`: 遵循JSON Schema

#### `app/core/model_router.py` - 智能模型路由
- **功能**：根据任务类型和条件智能选择LLM配置
- **路由规则**：
  - 不同任务类型选择不同配置
  - 可配置的路由策略（如优先选择快速模型或高能力模型）
  - 记录选择原因用于分析

#### `app/core/jira_client.py` - Jira集成
- **功能**：
  - 解析Jira问题键（如"PROJ-123"）
  - 处理ADF（Atlassian Document Format）文档格式
  - 提取文本内容和嵌入的图片
  - 处理Jira HTML特殊格式
- **支持**：Word(.docx)文档导入和转HTML

#### `app/api/requirements.py` - 需求管理API
- **操作**：
  - 需求的CRUD操作
  - 从Jira、URL或文件导入需求
  - 生成需求HTML预览（使用Mammoth库处理Word）
  - 获取需求版本历史
- **导入方式**：
  - Jira问题链接
  - HTTP(S) URL
  - Excel/Word文件上传

#### `app/api/ai.py` - AI评审和生成API
- **评审检查项**（4个维度）：
  - 可测性分析：验收标准和测试数据
  - 可行性分析：技术依赖和性能约束
  - 逻辑分析：流程闭环和异常处理
  - 清晰度分析：术语统一和歧义规避
- **自动化**：
  - 异步后台任务执行评审
  - 支持长时间运行的评审
  - 实时进度反馈

#### `app/api/test_cases.py` - 测试用例管理
- **功能**：
  - 测试用例CRUD
  - 测试模块组织
  - 需求与用例的映射关系
  - 批量导入和导出

### 前端框架说明

#### `frontend/src/App.jsx` - 主应用组件
- **模块切换**：
  - 项目管理（项目列表、创建、编辑删除）
  - 需求管理（需求列表、导入、评审）
  - 用例管理（测试用例、测试模块组织）
  - LLM配置（模型参数、多配置切换）
  - 提示词管理（模板编辑、版本管理）

- **核心功能**：
  - 四维度需求评审：点击"评审"启动后台任务
  - 实时进度展示：评审运行状态、错误提示
  - 测试用例自动生成：基于需求和LLM配置

#### `frontend/src/api.js` - API调用层
- **请求封装**：所有HTTP请求的统一出口
- **错误处理**：统一的错误捕获和提示
- **超时管理**：30秒默认超时
- **关键函数**：
  - `getRequirements()`, `createProject()` 等CRUD
  - `startRequirementReview()`: 启动异步评审任务
  - `getReviewRunStatus()`: 轮询评审进度

#### `frontend/src/LlmConfigPage.jsx` - LLM配置管理
- 配置列表、新建、编辑、删除
- 支持多个配置并行存在
- 参数配置：温度、最大tokens、超时时间等

#### `frontend/src/PromptManagementPage.jsx` - 提示词管理
- 提示词模板的CRUD
- 支持不同提示词类型（需求评审、用例生成等）
- 启用/禁用模板
- 版本管理

#### `frontend/src/TestCaseWorkflowPage.jsx` - 测试用例工作流
- 测试模块树形结构组织
- 在模块下编辑测试用例
- 关联到需求
- 支持思维导图可视化（Mind Elixir）

---

## 快速开始

### 前置条件

- Python 3.9+
- Node.js 16+
- MySQL 8.0+
- Docker & Docker Compose（可选）

### 方式一：本地开发（推荐）

#### 1. 启动MySQL

```bash
# 使用Docker Compose启动MySQL
docker-compose -f docker-compose.mysql.yml up -d

# 等待MySQL完全启动（约30秒）
# 验证连接
mysql -h 127.0.0.1 -u aitest -p -e "SELECT VERSION();"
# 密码: aitest123456
```

#### 2. 启动后端

```bash
cd backend

# 创建虚拟环境（可选但推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制示例文件并修改）
cp .env.example .env
# 编辑.env文件，设置AITEST_DATABASE_URL等

# 启动FastAPI服务
uvicorn app.main:app --reload --port 8001
```

**验证后端：**
- 健康检查：http://localhost:8001/health
- Swagger文档：http://localhost:8001/swagger

#### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（Vite）
npm run dev
```

**前端地址：** http://localhost:5174 或 http://localhost:5173（Vite自动分配）

### 方式二：Docker部署（待完善）

```bash
# 整体启动（需要完整的docker-compose配置）
docker-compose up -d
```

---

## 关键配置说明

### 后端配置文件（`.env`）

```bash
# 数据库连接
AITEST_DATABASE_URL=mysql+pymysql://aitest:aitest123456@127.0.0.1:3306/aitest

# LLM配置（默认值，可通过API覆盖）
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4-0125-preview
OPENAI_API_KEY=your-key-here

# Jira配置（可选）
JIRA_BASE_URL=https://jira.company.com
```

### 前端配置（`frontend/src/api.js`）

```javascript
const ASSET_BASE_URL = "http://localhost:8001/assets";
const API_BASE_URL = "http://localhost:8001/api";
const API_TIMEOUT = 30000; // 30秒
```

### MySQL初始化脚本

- 脚本位置：`backend/sql/init/001_init_aitest.sql`
- 执行时机：Docker启动时自动执行
- 内容：创建所有必要的表、索引和序列初始值

---

## 工作流示例

### 场景：完整的需求评审到用例生成

1. **创建项目**
   - 前端 → 项目管理 → 新建 → 输入项目名和描述

2. **导入需求**
   - 需求管理 → 导入需求
   - 支持：Jira链接、URL、Word/Excel文件

3. **查看需求预览**
   - 需求列表 → 点击需求 → 查看生成的HTML预览

4. **启动AI评审**
   - 需求列表 → 右键菜单 → 选择评审维度 → "评审"
   - 后端异步执行，前端轮询进度
   - 评审项目：可测性、可行性、逻辑、清晰度

5. **查看评审结果**
   - 需求详情 → 评审历史 → 查看每个维度的建议

6. **生成测试用例**
   - 用例管理 → 新建模块 → 生成用例
   - AI根据需求内容和评审结果自动生成

7. **编辑和组织用例**
   - 在模块中手动编辑、添加或删除用例
   - 结构化保存和管理

---

## 技术亮点

### 1. 异步评审引擎
- 长时间运行的AI评审任务在后台执行
- 前端通过轮询获取进度，不阻塞UI
- 支持并行评审多个需求

### 2. 智能模型路由
- 根据任务类型和负载自动选择合适的LLM
- 支持多个不同配置的LLM服务商
- 可配置的路由策略和降级方案

### 3. 灵活的提示词管理
- 中心化的提示词模板库
- 支持不同任务类型的提示词
- 可以实时更新无需重启服务

### 4. 多格式需求导入
- Jira问题集成（ADF格式解析）
- Word(.docx)文档支持（使用Mammoth库）
- URL和本地文件上传
- 自动HTML预览生成

### 5. 完整的版本管理
- 需求版本历史记录
- 评审运行存档
- 支持版本对比和回溯

---

## 常见操作

### 查看日志

```bash
# FastAPI服务日志
tail -f backend/logs/*.log

# MySQL日志
docker logs aitest-mysql
```

### 数据库查询

```bash
# 连接MySQL
mysql -h 127.0.0.1 -u aitest -p aitest

# 查看所有表
SHOW TABLES;

# 查看项目列表
SELECT id, name, creator, created_at FROM projects;
```

### 重置开发环境

```bash
# 停止并删除Docker容器
docker-compose -f docker-compose.mysql.yml down

# 移除本地数据
docker volume rm aitest-mysql

# 重新启动
docker-compose -f docker-compose.mysql.yml up -d
```

---

## 项目依赖

### 后端依赖（`backend/requirements.txt`）

| 包名 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.116.1 | Web框架 |
| uvicorn | 0.35.0 | ASGI服务器 |
| SQLAlchemy | 2.0.36 | ORM框架 |
| PyMySQL | 1.1.1 | MySQL驱动 |
| Pydantic | 2.11.7 | 数据验证 |
| httpx | 0.28.1 | HTTP客户端 |
| Mammoth | 1.8.0 | Word转HTML |

### 前端依赖（`frontend/package.json`）

| 包名 | 版本 | 用途 |
|------|------|------|
| React | 18.3.1 | UI框架 |
| React DOM | 18.3.1 | React DOM |
| Vite | 5.4.11 | 构建工具 |
| Mind Elixir | 5.9.3 | 思维导图 |

---

## 开发指南

### 添加新的API端点

1. 在 `backend/app/api/` 中创建新的模块文件（如 `new_feature.py`）
2. 定义FastAPI路由和Pydantic模型
3. 在 `app/main.py` 中导入并注册路由
4. 在前端 `src/api.js` 中添加对应的API调用包装

### 修改数据库表结构

1. 创建新的SQL迁移脚本：`backend/sql/init/002_*.sql`
2. 连接到MySQL执行脚本
3. 在 `memory_db.py` 中更新相应的数据访问代码

### 更新LLM提示词

1. 进入前端的"提示词管理"页面
2. 创建或修改模板
3. 系统自动保存到数据库
4. 重新启动评审任务时自动应用新提示词

---

## 故障排查

### 后端连接MySQL失败

```bash
# 检查MySQL是否运行
docker ps | grep mysql

# 检查连接参数
mysql -h 127.0.0.1 -u aitest -paitest123456 -e "SELECT 1;"

# 检查.env文件中的AITEST_DATABASE_URL
```

### 前端无法连接后端

```bash
# 检查后端是否运行
curl http://localhost:8001/health

# 检查CORS配置（main.py中的CORSMiddleware）
# 检查前端api.js中的API_BASE_URL
```

### 需求评审任务超时

- 增加LLM配置中的timeout参数
- 或者分割大型需求为多个小需求再评审

---

## 未来计划

- [ ] 多语言界面支持
- [ ] 评审结果的可视化仪表板
- [ ] 集成更多第三方需求源（Azure DevOps、GitHub等）
- [ ] 用例执行集成（Selenium、API测试）
- [ ] 性能优化和缓存层
- [ ] 完整的Docker Compose生产部署配置

---

## 许可证

（根据项目需要补充）

## 贡献指南

（根据项目需要补充）

## 联系方式

（根据项目需要补充）
