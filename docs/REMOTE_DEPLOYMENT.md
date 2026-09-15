<div align="center">

<h1>VPS 与 Authentik 部署模板</h1>

<p>让公网入口经过身份网关，再把生成请求送回本地 GPU</p>

</div>

## 1 信任边界

本机继续只监听回环地址

- Next.js `127.0.0.1:3000`
- FastAPI `127.0.0.1:8001`
- ComfyUI `127.0.0.1:8188`

公网只访问 VPS 上的反向代理和 Authentik

不要把 ComfyUI 或 FastAPI 端口直接映射到公网

## 2 推荐链路

- 浏览器连接 VPS 上的 HTTPS 域名
- 反向代理把未登录请求交给 Authentik
- Authentik 完成身份验证并返回受保护会话
- VPS 通过持久反向 SSH 隧道访问本机 Next.js
- Next.js 的同源 `/api` 代理再访问本机 FastAPI
- FastAPI 通过本机回环地址访问 ComfyUI

这种结构让浏览器不直接知道后端或 ComfyUI 地址

## 3 占位配置

```text
PUBLIC_HOST=studio.example.com
VPS_SSH_HOST=gpu-gateway.example.invalid
VPS_TUNNEL_PORT=13000
LOCAL_STUDIO_URL=http://127.0.0.1:3000
```

以上均为无效示例值，不要把真实主机、用户名、私钥路径或令牌提交到 Git

## 4 启动反向隧道

先确认工作台已经在本机 `127.0.0.1:3000` 运行，再使用本机 SSH 配置中的别名启动隧道

```powershell
pwsh -File .\scripts\Start-RemoteTunnel.ps1 `
  -SshAlias 'your-vps-alias' `
  -RemotePort 14280
```

脚本会执行以下检查：

- 本机前端端口正在监听
- SSH 使用非交互模式并在转发失败时立即退出
- VPS 只监听 `127.0.0.1:14280`
- VPS 可以通过隧道读取工作台首页
- PID 和日志保存在 D 盘运行区，不进入 Git

停止隧道：

```powershell
pwsh -File .\scripts\Stop-RemoteTunnel.ps1
```

## 5 Authentik 最小要求

- 使用反向代理或 outpost 保护完整站点
- 默认拒绝匿名访问
- 只向授权用户组开放生成页面
- 会话 Cookie 使用 `Secure`、`HttpOnly` 和适当的 `SameSite` 策略
- 对登录和生成入口设置速率限制
- 日志不记录提示词全文、上传文件内容、Cookie 或授权头

## 6 Nginx 上游

Nginx 或其他反向代理的最终上游应指向 VPS 回环端口：

```nginx
proxy_pass http://127.0.0.1:14280;
```

站点继续复用 VPS 现有的证书、身份校验和身份请求头片段

不要让反向代理绕过身份校验，也不要把 `14280` 绑定到公网地址

## 7 远程执行约束

- GPU 队列保持串行，避免 H3 与 SeedVR2 同时占用显存
- 上传大小、文件扩展名和项目标识在后端继续校验
- 输出只从项目根目录下的安全资源路径提供
- Authentik 只负责身份入口，不替代应用侧路径校验和任务隔离
- 隧道断开时保留本地任务记录，前端恢复后继续轮询

## 8 上线前验收

- HTTPS 证书有效，HTTP 自动跳转 HTTPS
- 匿名访问被 Authentik 拦截
- 登录后只能访问前端，无法直接访问 ComfyUI
- 生成、刷新、断线重连和任务完成通知均正常
- 大文件上传限制与超时符合 15 秒视频工作流
- 日志和错误页不包含本地绝对路径、凭据或内部主机
- 反向隧道服务能在本机或 VPS 重启后恢复

真实域名、SSH 别名和 Authentik 应用编号只放在部署主机的秘密管理或环境配置中
