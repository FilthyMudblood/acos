# Supabase 云端审计日志配置（一步步）

当前端配置了 Supabase 后，每次对话执行成功并写入审计，会把一条记录插入表 **`agentos_public_logs`**。你在 **Supabase 网页控制台**里即可查询、导出。

---

## 你需要完成的步骤（网页 / 控制台）

### 1. 创建 Supabase 项目（若还没有）

1. 打开 [https://supabase.com](https://supabase.com) 并登录。  
2. **New project** → 选组织、数据库密码、区域 → 等待项目就绪。

### 2. 拿到两个关键字符串

在 Supabase 左侧 **Project Settings**（齿轮）→ **API**：

| 名称 | 用途 |
|------|------|
| **Project URL** | 对应环境变量 `SUPABASE_URL`（形如 `https://xxxx.supabase.co`） |
| **service_role** `secret`（在 *Project API keys* 里） | 对应 `SUPABASE_SERVICE_ROLE_KEY` |

**注意：** `service_role` 权限极高，**只能放在服务器**（`.env`、`secrets.toml`、systemd），**不要**提交到 Git，**不要**放进浏览器前端或公开仓库。

### 3. 在数据库里建表

1. 左侧 **SQL Editor** → **New query**。  
2. 把本仓库文件 **`docs/supabase_agentos_logs.sql`** 的**全部内容**粘贴进去。  
3. 点击 **Run**。应无报错；会创建 `agentos_public_logs`（以及可选的 `agentos_logs` 等）。

### 4. 把密钥写进 AgentOS 运行环境（三选一）

任选一种你当前部署用的方式：

**A. 项目根目录 `.env`（本地 / 简单服务器）**

复制 `.env.example` 为 `.env`，填写：

```env
SUPABASE_URL=https://你的项目.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**B. 项目根目录 `.streamlit/secrets.toml`（推荐与 Streamlit 金库一致）**

复制 `.streamlit/secrets.toml.example` 为 `secrets.toml`，在同文件中加入：

```toml
SUPABASE_URL = "https://你的项目.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJ..."
```

**C. systemd / 容器环境变量**

在服务的 `Environment=` 或 `EnvironmentFile=` 里导出同上两个变量。

### 5. 重启前端进程

例如：`systemctl restart acos`（或你的服务名），确保新环境变量被加载。

### 6. 验证是否写入成功

1. 打开你的 AgentOS 页面，在 **I/O Terminal** 里随便发一条会成功跑完的任务。  
2. 打开 Supabase → **Table Editor** → 表 **`agentos_public_logs`** → 应出现新行。  
3. 若前端出现 **「Cloud log write failed」** toast，到服务器看 Streamlit 日志，或检查 URL/密钥是否多空格、表是否已创建。

---

## 在哪里「看」日志？

- **Supabase 控制台**：**Table Editor** → **`agentos_public_logs`**（或 **SQL Editor** 写 `select * from public.agentos_public_logs order by created_at desc limit 50;`）。  
- **可读列名视图（推荐分析/导出）**：`select * from public.agentos_public_logs_readable order by "Timestamp" desc limit 50;`  
- **应用内**：**System Telemetry** → **Execution Audit Log** 仍是当前浏览器会话里的表；Supabase 里是**跨会话、持久化**的备份。

---

## 仓库里已替你接好的部分（无需你再写代码）

- `backend/supabase_logger.py`：`insert_public_log` 写入 `agentos_public_logs`。  
- `frontend/app_os_terminal.py`：当 `SUPABASE_URL` 与 `SUPABASE_SERVICE_ROLE_KEY` 均存在时，每次运行结束后尝试插入。  
- `.env.example`、`.streamlit/secrets.toml.example`：示例变量名。  
- 根目录 `secrets.toml` 注入逻辑已包含上述两个 Supabase 变量。

若你只配了 URL 没配 service key（或反过来），**不会写云**，也不会报错阻塞页面，只是没有云端记录。
