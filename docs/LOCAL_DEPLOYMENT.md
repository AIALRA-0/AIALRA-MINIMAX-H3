<div align="center">

<h1>本地部署说明</h1>

<p>Windows、RTX 4080 16GB 与 D 盘临时运行区</p>

</div>

## 1 硬件与软件前提

- Windows 11 与支持当前 PyTorch CUDA 轮子的 NVIDIA 驱动
- RTX 4080 16GB
- 64GB 系统内存
- PowerShell 7、Git、Python 3.12、Node.js 与 npm
- D 盘至少预留约 80 GiB，真实生成还需要额外输出空间

安装脚本使用独立虚拟环境，不修改系统 Python 包

## 2 目录布局

默认 `RuntimeRoot` 为 `D:\AIALRA-MINIMAX-H3`

- `ComfyUI` 保存固定版本的 ComfyUI 与自定义节点
- `models` 保存模型权重
- `venvs` 保存 ComfyUI 与后端 Python 环境
- `cache` 保存 Hugging Face、pip 和 npm 缓存
- `outputs\comfyui` 保存 ComfyUI 原始输出
- `outputs\studio` 保存项目、标准化视频、抽帧与母版
- `logs` 保存服务日志
- `pids` 保存启动器进程编号
- `tools` 保存经哈希核对的 Civitai MCP 命令行客户端

D 盘路径是过渡性存储，不表示最终必须使用 D 盘

## 3 安装

```shell
# 从仓库根目录安装应用和固定版本依赖
pwsh -File .\scripts\Install-Local.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'
```

安装器遇到已修改的第三方依赖仓库时会停止，避免覆盖本地改动

```shell
# 明确确认已阅读模型条款后下载模型
pwsh -File .\scripts\Download-Models.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3' -AcceptModelTerms
```

下载器只使用清单中的 Hugging Face 仓库与文件名，并在结束时核对每个文件的精确字节数

可选 Ref2VA 模型约增加 22.9 GB，当前 16GB 主链路不需要它

```shell
# 只有确实需要完整 Ref2VA 时才添加此开关
pwsh -File .\scripts\Download-Models.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3' -AcceptModelTerms -IncludeRef2VA
```

## 4 启动与停止

```shell
# 启动 ComfyUI，默认端口为 8188
pwsh -File .\scripts\Start-ComfyUI.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'

# 启动 FastAPI 与 Next.js，默认端口为 8001 和 3000
pwsh -File .\scripts\Start-Studio.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'
```

两个脚本都只监听 `127.0.0.1`

```shell
# 检查 HTTP 状态、启动器 PID、监听器 PID 和显存
pwsh -File .\scripts\Get-LocalStatus.ps1

# 停止已验证为本项目的监听器与启动器
pwsh -File .\scripts\Stop-Local.ps1
```

`Stop-Local.ps1` 会先核对端口和命令行，发现未知进程时停止操作并报告，不会根据模糊进程名批量终止

## 5 首次工作流

- 第一步，打开 `http://127.0.0.1:3000` 并进入演示项目
- 第二步，在素材检查器中确认图片模型显示 `FLUX.2 Klein 4B (ComfyUI)`
- 第三步，在视频检查器中确认视频模型显示 `MiniMax H3 (ComfyUI)`
- 第四步，使用 0.2 MP、8 步、15 秒草稿预设提交视频
- 第五步，等待队列完成后执行智能抽帧
- 第六步，查看 8 张排序结果并确认人物与动作
- 第七步，执行 SeedVR2 2× 母版并把结果加入时间线

## 6 显存共存策略

如果实时翻译、Ollama 或其他 CUDA 任务已经占用显存，让先开始的任务自然结束

不要终止其他 GPU 任务，也不要同时提交 H3 与 SeedVR2

ComfyUI 自身使用串行队列，工作台的任务映射持久化到 SQLite，刷新页面不会丢失已提交任务

Windows 下缺少 Triton 时，KJNodes 的 `PatchTritonVAE` 会显示可选节点警告，当前工作流不依赖它，不需要为此安装非官方 Triton 包

## 7 故障定位

- ComfyUI 未启动时查看 `D:\AIALRA-MINIMAX-H3\logs\comfyui.stderr.log`
- 后端未启动时查看 `D:\AIALRA-MINIMAX-H3\logs\backend.stderr.log`
- 前端未启动时查看 `D:\AIALRA-MINIMAX-H3\logs\frontend.stderr.log`
- 模型缺失时重新运行下载脚本，它只补齐大小不匹配或不存在的文件
- 端口被占用时先运行状态脚本，确认是否属于本项目，再决定停止或更换端口
- CUDA 内存不足时先等待其他任务结束，再降低草稿像素或缩短测试片段，不修改母版流程定义

## 8 迁移回目标盘

- 第一步，运行停止脚本并确认三个端口不再监听
- 第二步，核对目标盘可用空间大于运行区总大小与后续输出余量
- 第三步，把整个 `RuntimeRoot` 迁移到目标位置并核对文件数量与模型字节数
- 第四步，用新的 `-RuntimeRoot` 启动服务
- 第五步，运行状态脚本与工作流校验器

不要清理来源不明的备份、缓存或其他项目目录，本仓库只管理自己的明确运行区
