# 测试说明

## 关于测试数据库

**您不需要手动创建数据库！** 测试使用 SQLite 内存数据库，这意味着：

- ✅ 测试会自动创建和销毁数据库
- ✅ 每个测试用例使用独立的数据库实例
- ✅ 测试运行速度快
- ✅ 无需配置外部数据库服务

## 安装测试依赖

```bash
# 使用 uv（推荐）
uv sync --dev

# 或使用 pip
pip install -e ".[dev]"
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_user_service.py
pytest tests/test_auth_api.py
pytest tests/test_dependencies.py

# 运行特定测试用例
pytest tests/test_user_service.py::TestUserService::test_register_user_success

# 显示详细输出
pytest -v

# 显示覆盖率报告
pytest --cov=app --cov-report=html
```

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # pytest 配置和 fixtures
├── test_user_service.py     # 用户服务测试
├── test_auth_api.py         # 认证 API 测试
└── test_dependencies.py     # 依赖注入测试
```

## 测试覆盖的功能

### 用户服务测试 (test_user_service.py)
- ✅ 用户注册（成功、重复用户名、重复邮箱）
- ✅ 用户认证（成功、错误密码、不存在用户、非活跃用户）
- ✅ 获取用户信息
- ✅ 修改密码（成功、错误旧密码、不存在用户）
- ✅ 密码重置请求（成功、不存在邮箱）
- ✅ 密码重置（成功、无效验证码、不存在邮箱）

### 认证 API 测试 (test_auth_api.py)
- ✅ 用户注册 API
- ✅ 用户登录 API
- ✅ 获取当前用户信息 API
- ✅ 修改密码 API
- ✅ 密码重置请求 API
- ✅ 密码重置 API

### 依赖注入测试 (test_dependencies.py)
- ✅ get_current_user（成功、无效 token、不存在用户、非活跃用户、缺少 sub）

## Fixtures

测试中可用的 fixtures：

- `db_session`: 异步数据库会话（每个测试用例独立）
- `async_client`: 异步 HTTP 测试客户端
- `test_user_data`: 测试用户数据
- `test_user_data_2`: 第二个测试用户数据

## 注意事项

1. **环境变量**: 测试会自动设置必要的环境变量（`DATABASE_URL` 和 `SECRET_KEY`）
2. **邮件发送**: 测试中会 mock 邮件发送功能，不会实际发送邮件
3. **数据库隔离**: 每个测试用例使用独立的数据库实例，互不干扰
4. **异步支持**: 所有测试都使用 `pytest-asyncio` 支持异步操作

## 故障排除

如果遇到导入错误，确保：
1. 已安装所有开发依赖：`uv sync --dev`
2. 在项目根目录运行测试
3. Python 版本 >= 3.10

