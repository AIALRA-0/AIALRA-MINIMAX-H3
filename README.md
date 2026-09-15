<div align="center">

<h1>AIALRA MiniMax H3 Studio</h1>

<p>面向 RTX 4080 16GB 的本地 AI 短剧工作台，从 15 秒低分辨率草稿到 2× 高清母版</p>

<p><strong>Windows 本地优先 · 默认中文 · 无付费模型接口 · 已在 RTX 4080 16GB 完成端到端实测</strong></p>

<p><a href="README.en.md">English</a> · <a href="docs/LOCAL_DEPLOYMENT.md">部署说明</a> · <a href="docs/VALIDATION.md">验证记录</a> · <a href="docs/RESEARCH.md">选型依据</a></p>

</div>

## 1 项目定位

本仓库基于 [AI Movie Studio 2](https://github.com/Heroesjouney/AIMovieStudiov2) 构建，并针对单机 Windows 环境收紧了模型与工作流范围

目标配置使用 RTX 4080 16GB 显存和 64GB 系统内存

核心链路包括：

- 使用 FLUX.2 Klein 4B 生成角色、场景和首帧
- 使用 MiniMax H3 INT8 与 8 步 LoRA 生成最长 15 秒的视频草稿
- 把草稿统一为 15 秒、24 FPS、H.264/AAC 的交付格式
- 按清晰度、曝光、边缘信息和时间分布对候选帧排序
- 使用 SeedVR2 3B INT8 对选定视频执行 2× 超分
- 在时间线中管理镜头、候选版本、音频和拼接结果
- 使用 H3 Continuum V3.8 分段审片、局部重生成和断点续跑

前端支持中文与英文切换，首次打开默认中文

## 2 第一次成功

安装程序会把模型、虚拟环境、缓存和输出放到 D 盘运行区，仓库源码不承载大模型文件

```shell
# 安装固定版本的 ComfyUI、社区节点、后端与前端依赖
pwsh -File .\scripts\Install-Local.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'

# 阅读各模型许可后下载并核对官方 Hugging Face 文件大小
pwsh -File .\scripts\Download-Models.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3' -AcceptModelTerms

# 启动只监听本机回环地址的 ComfyUI
pwsh -File .\scripts\Start-ComfyUI.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'

# 启动后端与生产版前端
pwsh -File .\scripts\Start-Studio.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'
```

打开 `http://127.0.0.1:3000`，正常结果是项目页显示中文界面、状态为已连接、图片模型只有 FLUX.2 Klein、视频模型只有 MiniMax H3

```shell
# 查看三个本地服务与当前显存状态
pwsh -File .\scripts\Get-LocalStatus.ps1

# 停止本仓库启动的服务，命令会校验监听端口和进程命令行
pwsh -File .\scripts\Stop-Local.ps1
```

完整前提、磁盘布局和故障处理见 [本地部署说明](docs/LOCAL_DEPLOYMENT.md)

## 3 草稿到母版工作流

- 第一步，在素材页使用 FLUX.2 Klein 制作角色图、场景图或首帧
- 第二步，在视频页选择 MiniMax H3，草稿档使用约 0.2 MP、8 步和 15 秒
- 第三步，生成完成后执行智能抽帧，系统默认从全片候选中选择 8 张分布均匀的高分帧
- 第四步，确认人物、构图和动作后执行 SeedVR2 2× 母版
- 第五步，把标准化后的 15 秒母版加入时间线，并按镜头顺序拼接或导出

MiniMax H3 的真实生成会占用大量显存，启动前请让翻译、语言模型或其他 CUDA 任务自然结束，不要终止其他任务来抢占 GPU

## 4 已固定的本地组件

- ComfyUI `0.35.0`，固定到仓库提交 `36da3ff`
- MiniMax H3 FL2VA INT8、Qwen3-VL NVFP4、视频 VAE、音频 VAE 与官方 8 步 LoRA
- SeedVR2 3B INT8 与 FP16 VAE
- FLUX.2 Klein Base 4B FP8、Qwen 3 4B 文本编码器与 FLUX.2 VAE
- KJNodes、VideoHelperSuite 与 MiniMax H3 Prompt Writer
- H3 Continuum `3.8.2`，固定到仓库提交 `c38c616`
- Civitai 官方 MCP，只用于公开元数据和版本调查，不保存浏览器 Cookie 或账户凭据

模型文件不会进入 Git，下载清单与预期字节数位于 [`config/model-manifest.json`](config/model-manifest.json)

## 5 当前验证状态

截至 2026-09-15 已完成：

- 后端测试 `15 passed`
- 前端生产构建、ESLint 与 TypeScript 检查通过
- 三份 ComfyUI API 工作流通过真实 `object_info` 节点和选项校验
- H3 Continuum 上游测试 `1260 passed`、`2 skipped`，其中一项先受 Windows GBK 影响，切换 UTF-8 后复跑通过
- CPU 媒体链路完成 15.2 秒输入到精确 15.0 秒、24 FPS、360 帧和 AAC 输出
- 智能抽帧完成 8 张候选排序与文件写入
- 中文默认界面与英文切换经过本地浏览器验证
- FLUX.2 Klein 真实 512×512 首帧约 17 秒完成
- MiniMax H3 真实 15 秒草稿为 608×352、24 FPS、360 帧，约 5 分 55 秒完成
- SeedVR2 真实全片 2× 母版为 1216×704、24 FPS、360 帧，约 2 小时 32 分完成
- 全片母版保留 15.000 秒 H.264 视频与 AAC 立体声音频，三处抽样画面的人物、服装、列车和色调连续
- 发布候选的工作区与完整提交历史通过 Gitleaks，均为 `no leaks found`
- [公开 GitHub 仓库](https://github.com/AIALRA-0/AIALRA-MINIMAX-H3) 已建立
  - 前端镜像构建通过
  - 后端镜像构建通过
  - Compose 启动、健康检查与代理冒烟测试通过
- VPS 回环反向隧道已建立并返回 HTTP 200，本机远程配置使用锁定模式

全片 2× 超分可以在 16GB 显存上运行，但生产环境更适合按短镜头或短片段超分后拼接，以缩短失败重试和审片周期

公网域名与身份网关路由仍待确认最终主机名，未完成项目不会被描述为通过

详细命令、产物和限制见 [验证记录](docs/VALIDATION.md)

## 6 存储与迁移

默认运行区是 `D:\AIALRA-MINIMAX-H3`，用于缓解源码盘空间压力

其中 `models`、`cache`、`outputs`、`venvs` 和 `ComfyUI` 都是可迁移目录，后续把 `-RuntimeRoot` 改到目标盘即可重新安装或迁移

迁移前先停止本仓库服务，再核对目标盘空间和文件字节数，不对未知目录执行批量删除

## 7 远程访问边界

默认服务只监听 `127.0.0.1`，不会直接向公网暴露 ComfyUI 或 FastAPI

推荐通过 VPS 反向隧道接入，并由 Authentik 负责登录、会话和访问策略，公网只开放经过网关的前端入口

仓库不保存真实域名、SSH 主机、令牌、Cookie、API 密钥或 Authentik 客户端密钥，部署模板见 [VPS 与 Authentik 说明](docs/REMOTE_DEPLOYMENT.md)

## 8 调研与社区资源

当前组合来自官方 ComfyUI、Hugging Face、MiniMax、Black Forest Labs、SeedVR2、社区节点源码和 Civitai MCP 元数据的交叉核对

没有直接安装来源不明、许可不清或与 16GB 路径重复的工作流，筛选结果、Civitai 模型编号和低配工作流对照见 [选型依据](docs/RESEARCH.md)

## 9 许可与致谢

本仓库沿用上游的 [GNU Affero General Public License v3.0](LICENSE)

托管修改版服务时需要遵守 AGPL-3.0 的网络交互源码提供要求，模型权重、LoRA 和第三方节点仍分别受其原始许可约束

主要上游与维护者包括：

- [AI Movie Studio 2](https://github.com/Heroesjouney/AIMovieStudiov2)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [MiniMax H3](https://github.com/MiniMax-AI/MiniMax-H3)
- [SeedVR2](https://github.com/ByteDance-Seed/SeedVR)
- [FLUX.2](https://github.com/black-forest-labs/flux2)
- 选型记录中列出的社区维护者
