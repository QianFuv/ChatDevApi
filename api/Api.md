# ChatDev API 文档

ChatDev API 提供了一种以编程方式访问 ChatDev 的能力，允许开发者使用 REST API 调用自动生成软件并构建 Android APK。

## 基本信息

- **基础URL**: `http://your-server:8000/api/v1`
- **内容类型**: application/json
- **认证**: 需要 OpenAI API 密钥

## 认证

所有 API 调用都需要一个有效的 OpenAI API 密钥。密钥可以在请求头中提供：

```
X-API-Key: sk-your-openai-api-key
```

或者作为请求体的一部分：

```json
{
  "api_key": "sk-your-openai-api-key",
  ...
}
```

## API 端点

### 1. 生成软件

启动一个新的 ChatDev 生成任务。

- **URL**: `/generate`
- **方法**: POST
- **描述**: 该端点启动一个新的软件生成任务，使用提供的配置。任务将异步在后台运行，并返回一个任务 ID。

#### 请求参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| api_key | string | 是 | 用于认证的 OpenAI API 密钥 |
| base_url | string | 否 | API 调用的可选基础 URL（用于代理或替代端点） |
| task | string | 是 | 要构建的软件描述（10-2000个字符） |
| name | string | 是 | 软件项目的名称（只能包含字母、数字、下划线和连字符） |
| config | string | 否 | CompanyConfig/ 下的配置名称（默认: "Default"，可选: "Art", "Human", "Flet", "Incremental") |
| org | string | 否 | 组织名称（默认: "DefaultOrganization"） |
| model | string | 否 | 要使用的 LLM 模型（默认: "CLAUDE_3_5_SONNET"，可选: "GPT_3_5_TURBO", "GPT_4", "GPT_4_TURBO", "GPT_4O", "GPT_4O_MINI", "DEEPSEEK_R1"） |
| path | string | 否 | 用于增量开发的现有代码路径 |
| build_apk | boolean | 否 | 是否在生成软件后构建 APK（默认: false） |

#### 请求示例

```json
{
  "api_key": "sk-...",
  "task": "Create a simple todo list application with a GUI interface",
  "name": "TodoApp",
  "config": "Default",
  "org": "MyOrganization",
  "model": "CLAUDE_3_5_SONNET",
  "build_apk": true
}
```

#### 响应参数

| 参数 | 类型 | 描述 |
|------|------|------|
| task_id | integer | 任务的唯一标识符 |
| status | string | 任务的当前状态 |
| created_at | string | 创建时间戳（ISO格式） |

#### 响应示例

```json
{
  "task_id": 1,
  "status": "PENDING",
  "created_at": "2024-03-13T14:30:00"
}
```

#### 状态码

- **201 Created**: 成功创建任务
- **400 Bad Request**: 请求参数无效
- **401 Unauthorized**: API 密钥无效
- **422 Unprocessable Entity**: 验证错误
- **500 Internal Server Error**: 服务器错误

---

### 2. 获取任务状态

获取 ChatDev 生成任务的状态。

- **URL**: `/status/{task_id}`
- **方法**: GET
- **描述**: 该端点返回生成任务的当前状态。

#### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| task_id | integer | 要检查的任务的 ID |

#### 响应参数

| 参数 | 类型 | 描述 |
|------|------|------|
| task_id | integer | 任务的唯一标识符 |
| status | string | 任务的当前状态: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED |
| created_at | string | 任务创建时间戳（ISO格式） |
| updated_at | string | 最后更新时间戳（ISO格式） |
| result_path | string | 如果已完成，生成软件的路径 |
| apk_path | string | 如果已构建，APK 文件的路径 |
| error_message | string | 如果失败，错误消息 |

#### 响应示例

```json
{
  "task_id": 1,
  "status": "COMPLETED",
  "created_at": "2024-03-13T14:30:00",
  "updated_at": "2024-03-13T14:45:00",
  "result_path": "WareHouse/TodoApp_MyOrganization_20240313143000",
  "apk_path": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk",
  "error_message": null
}
```

#### 状态码

- **200 OK**: 成功获取任务状态
- **404 Not Found**: 任务不存在
- **500 Internal Server Error**: 服务器错误

---

### 3. 列出所有任务

列出所有 ChatDev 生成任务。

- **URL**: `/tasks`
- **方法**: GET
- **描述**: 该端点返回所有生成任务的列表，可选择按状态过滤。

#### 查询参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| status | string | 否 | 按状态过滤任务 (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED) |
| limit | integer | 否 | 返回的最大任务数量（默认: 10，最大: 100） |
| offset | integer | 否 | 要跳过的任务数量（默认: 0） |

#### 响应参数

| 参数 | 类型 | 描述 |
|------|------|------|
| tasks | array | 任务状态对象的数组 |
| total | integer | 任务总数 |

#### 响应示例

```json
{
  "tasks": [
    {
      "task_id": 1,
      "status": "COMPLETED",
      "created_at": "2024-03-13T14:30:00",
      "updated_at": "2024-03-13T14:45:00",
      "result_path": "WareHouse/TodoApp_MyOrganization_20240313143000",
      "apk_path": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk",
      "error_message": null
    },
    {
      "task_id": 2,
      "status": "RUNNING",
      "created_at": "2024-03-13T15:30:00",
      "updated_at": "2024-03-13T15:35:00",
      "result_path": null,
      "apk_path": null,
      "error_message": null
    }
  ],
  "total": 2
}
```

#### 状态码

- **200 OK**: 成功列出任务
- **422 Unprocessable Entity**: 验证错误
- **500 Internal Server Error**: 服务器错误

---

### 4. 取消任务

取消正在运行的 ChatDev 生成任务。

- **URL**: `/cancel/{task_id}`
- **方法**: POST
- **描述**: 该端点尝试取消正在运行的任务。

#### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| task_id | integer | 要取消的任务的 ID |

#### 请求参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| api_key | string | 是 | 用于认证的 OpenAI API 密钥 |

#### 请求示例

```json
{
  "api_key": "sk-..."
}
```

#### 响应参数

与获取任务状态的响应相同。

#### 响应示例

```json
{
  "task_id": 1,
  "status": "CANCELLED",
  "created_at": "2024-03-13T14:30:00",
  "updated_at": "2024-03-13T14:40:00",
  "result_path": null,
  "apk_path": null,
  "error_message": "Task cancelled by user"
}
```

#### 状态码

- **200 OK**: 成功取消任务
- **400 Bad Request**: 任务无法取消
- **401 Unauthorized**: API 密钥无效
- **404 Not Found**: 任务不存在
- **500 Internal Server Error**: 服务器错误

---

### 5. 删除任务记录

删除 ChatDev 任务记录。

- **URL**: `/task/{task_id}`
- **方法**: DELETE
- **描述**: 该端点从数据库中删除任务记录。它不会删除任何生成的文件。

#### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| task_id | integer | 要删除的任务的 ID |

#### 请求头

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| X-API-Key | string | 是 | 用于认证的 OpenAI API 密钥 |

#### 响应参数

| 参数 | 类型 | 描述 |
|------|------|------|
| message | string | 状态消息 |

#### 响应示例

```json
{
  "message": "Task 1 deleted successfully"
}
```

#### 状态码

- **200 OK**: 成功删除任务
- **401 Unauthorized**: API 密钥无效
- **404 Not Found**: 任务不存在
- **500 Internal Server Error**: 服务器错误

---

### 6. 构建 APK

从现有项目构建 Android APK。

- **URL**: `/build-apk`
- **方法**: POST
- **描述**: 该端点使用 GitHub Actions 工作流从现有 ChatDev 项目构建 Android APK。

#### 请求参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| api_key | string | 是 | 用于认证的 OpenAI API 密钥 |
| project_name | string | 是 | 要构建的项目名称 |
| organization | string | 否 | 项目路径中的组织名称 |
| timestamp | string | 否 | 项目路径中的时间戳 |

#### 请求示例

```json
{
  "api_key": "sk-...",
  "project_name": "TodoApp",
  "organization": "MyOrganization",
  "timestamp": "20240313143000"
}
```

#### 响应参数

| 参数 | 类型 | 描述 |
|------|------|------|
| success | boolean | 构建是否成功 |
| message | string | 状态消息 |
| apk_path | string | 构建的 APK 文件的路径 |
| artifacts | object | 生成的工件字典 |

#### 响应示例

```json
{
  "success": true,
  "message": "APK build completed successfully",
  "apk_path": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk",
  "artifacts": {
    "app-release.apk": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk"
  }
}
```

#### 状态码

- **200 OK**: 成功构建 APK
- **400 Bad Request**: 请求参数无效
- **401 Unauthorized**: API 密钥无效
- **404 Not Found**: 项目不存在
- **500 Internal Server Error**: 服务器错误

---

### 7. 健康检查

检查 API 是否正常运行。

- **URL**: `/health`
- **方法**: GET
- **描述**: 该端点返回 API 的当前状态和版本。

#### 响应参数

| 参数 | 类型 | 描述 |
|------|------|------|
| status | string | 健康状态 |
| version | string | API 版本 |
| timestamp | number | 当前时间戳 |

#### 响应示例

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": 1678735200.0
}
```

#### 状态码

- **200 OK**: API 正常运行

## 错误处理

所有错误响应都会返回一个包含以下字段的 JSON 对象：

| 参数 | 类型 | 描述 |
|------|------|------|
| error | string | 错误消息 |
| type | string | 错误类型 |

### 错误类型

- **authentication_error**: 认证失败
- **authorization_error**: 未授权
- **not_found_error**: 资源未找到
- **validation_error**: 验证错误
- **rate_limit_error**: 超出速率限制
- **server_error**: 服务器错误
- **task_cancellation_error**: 任务取消失败

### 错误示例

```json
{
  "error": "Invalid API key provided",
  "type": "authentication_error"
}
```

## 速率限制

API 实施速率限制以防止滥用。默认限制为每分钟 100 个请求。如果超出此限制，API 将返回 429 状态码。

速率限制信息包含在响应标头中：

- **X-RateLimit-Limit**: 在时间窗口内允许的最大请求数
- **X-RateLimit-Remaining**: 在当前窗口内剩余的请求数
- **X-RateLimit-Reset**: 当前速率限制窗口重置的时间戳

## 配置选项

ChatDev 支持几种不同的配置模式，可以通过设置请求中的 `config` 参数来使用：

### Default

基本软件开发流程，包括需求分析、编码、测试等阶段。

### Art

在默认流程的基础上添加了艺术设计阶段，允许生成和集成图像资源。

### Human

启用人机交互模式，允许用户在代码审查阶段参与开发过程。

### Flet

专为使用 Flet 框架开发的应用程序优化，特别适合构建跨平台应用。

### Incremental

用于在现有项目上进行增量开发，需要提供 `path` 参数指向现有代码。

## 使用示例

### Python

```python
import requests
import json

API_URL = "http://your-server:8000/api/v1"
API_KEY = "sk-your-openai-api-key"

# 生成新软件
def generate_software():
    url = f"{API_URL}/generate"
    payload = {
        "api_key": API_KEY,
        "task": "Create a simple todo list application with GUI",
        "name": "TodoApp",
        "config": "Default",
        "org": "MyOrganization",
        "model": "CLAUDE_3_5_SONNET",
        "build_apk": True
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# 检查任务状态
def check_task_status(task_id):
    url = f"{API_URL}/status/{task_id}"
    response = requests.get(url)
    return response.json()

# 取消任务
def cancel_task(task_id):
    url = f"{API_URL}/cancel/{task_id}"
    payload = {
        "api_key": API_KEY
    }
    response = requests.post(url, json=payload)
    return response.json()

# 主流程
if __name__ == "__main__":
    # 生成软件
    task = generate_software()
    print(f"Started task: {task['task_id']}")
    
    # 检查状态
    status = check_task_status(task['task_id'])
    print(f"Status: {status['status']}")
    
    # 等待完成（实际应用中应使用轮询或回调）
    import time
    while status['status'] in ['PENDING', 'RUNNING']:
        time.sleep(30)
        status = check_task_status(task['task_id'])
        print(f"Status: {status['status']}")
    
    if status['status'] == 'COMPLETED':
        print(f"Software generated at: {status['result_path']}")
        if status['apk_path']:
            print(f"APK built at: {status['apk_path']}")
    else:
        print(f"Task failed with error: {status['error_message']}")
```

### cURL

```bash
# 生成新软件
curl -X POST "http://your-server:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-your-openai-api-key",
    "task": "Create a simple todo list application with GUI",
    "name": "TodoApp",
    "config": "Default",
    "org": "MyOrganization",
    "model": "CLAUDE_3_5_SONNET",
    "build_apk": true
  }'

# 检查任务状态
curl -X GET "http://your-server:8000/api/v1/status/1"

# 取消任务
curl -X POST "http://your-server:8000/api/v1/cancel/1" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-your-openai-api-key"
  }'
```
