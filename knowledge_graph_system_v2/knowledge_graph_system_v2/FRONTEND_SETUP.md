# 前端配置说明 / Frontend Setup Guide

## 环境变量配置 / Environment Variables

### 1. 创建 .env 文件

在 `knowledge_graph_system_v2/knowledge_graph_system_v2/` 目录下创建 `.env` 文件：

```bash
cd knowledge_graph_system_v2\knowledge_graph_system_v2
copy .env.example .env
```

### 2. 配置 API 地址

编辑 `.env` 文件，设置后端 API 地址：

```env
VUE_APP_API_BASE=http://localhost:8000/api/v1
```

**注意**：
- 如果后端运行在其他端口，请修改为对应的地址
- 如果后端运行在其他机器，请使用对应的 IP 地址
- 确保后端服务已启动并可访问

### 3. 安装依赖

首次运行需要安装依赖：

```bash
npm install
```

### 4. 启动前端服务

```bash
npm run serve
```

前端将运行在 http://localhost:3000

## 常见问题 / Troubleshooting

### 问题 1: 无法连接到后端 API

**症状**: 前端页面显示网络错误或无法加载数据

**解决方案**:
1. 检查 `.env` 文件是否存在且配置正确
2. 确认后端服务已启动（访问 http://localhost:8000/health 测试）
3. 检查浏览器控制台是否有 CORS 错误
4. 确认后端 CORS 配置允许前端域名访问

### 问题 2: 端口 3000 被占用

**解决方案**:
```bash
# 查找占用端口的进程
netstat -ano | findstr :3000
taskkill /PID <进程ID> /F

# 或修改 vue.config.js 使用其他端口
```

### 问题 3: 依赖安装失败

**解决方案**:
```bash
# 清除缓存后重新安装
npm cache clean --force
npm install
```

### 问题 4: 页面显示空白

**解决方案**:
1. 检查浏览器控制台是否有 JavaScript 错误
2. 确认所有依赖已正确安装
3. 检查路由配置是否正确

## 开发说明 / Development Notes

- 前端使用 Vue 3 + TypeScript + Ant Design Vue
- API 调用统一通过 `@/api/http.ts` 封装
- 所有 API 请求会自动添加 baseURL 前缀
- 响应拦截器会自动处理错误并显示提示消息


