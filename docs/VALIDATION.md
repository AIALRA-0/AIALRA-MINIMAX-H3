<div align="center">

<h1>验证记录</h1>

<p>记录已执行检查、可复现命令和仍待完成的证据</p>

</div>

## 1 验证环境

- 日期 `2026-09-15`
- GPU `NVIDIA GeForce RTX 4080 16GB`
- 系统内存 `64GB`
- CPU `Intel Core i9-13900K`
- ComfyUI `0.35.0`
- PyTorch `2.14.0+cu130`
- 前端 Next.js `14.2.35`

## 2 已完成检查

```shell
# 后端单元与集成测试
& 'D:\AIALRA-MINIMAX-H3\venvs\studio-backend\Scripts\python.exe' -m pytest -q .\backend
```

结果为 `15 passed`

```shell
# 前端生产构建、ESLint 与 TypeScript 检查
npm --prefix .\frontend run build
```

结果为构建成功，共生成 6 个页面，项目工作区首载脚本约 470 kB

```shell
# 启动 CPU 校验实例并读取真实节点目录
pwsh -File .\scripts\Start-ComfyUI.ps1 -Port 8189 -CpuOnly -Foreground
```

真实 `object_info` 中检测到 MiniMax H3、SeedVR2、FLUX.2、Prompt Writer、KJNodes、VideoHelperSuite 与 H3 Continuum 节点

```shell
# 使用真实节点定义核对三个 API 工作流
& 'D:\AIALRA-MINIMAX-H3\venvs\studio-backend\Scripts\python.exe' .\backend\tools\validate_comfy_workflows.py --object-info-url http://127.0.0.1:8189/object_info
```

结果为 `minimax_h3.json`、`seedvr2_upscale.json` 和 `flux2.json` 全部通过

H3 Continuum 的完整上游测试首次得到 `1259 passed, 2 skipped, 1 failed`

唯一失败来自 Windows 默认 GBK 无法解码前端测试中的 Unicode 字符

```shell
# 在 UTF-8 环境复跑唯一失败项
$env:PYTHONUTF8='1'
& 'D:\AIALRA-MINIMAX-H3\venvs\comfyui\Scripts\python.exe' -m pytest -q tests\test_v38_public_surface_cleanup.py::test_intuitive_facade_is_discoverable_and_presentation_only
```

复跑结果为 `1 passed`，合计可确认 `1260 passed, 2 skipped`

## 3 CPU 媒体链路

测试输入为合成的 640×384、30 FPS、15.2 秒视频，并带 AAC 音频

标准化结果包括：

- 时长 `15.0` 秒
- 帧率 `24 FPS`
- 帧数 `360`
- 视频编码 `H.264`
- 音频存在且可探测

智能抽帧结果包括：

- 选择数量 `8`
- 采样覆盖完整视频时间范围
- 输出保存到项目 `pipeline` 目录
- 第一候选文件成功读取并完成像素检查

测试夹具与结果保存在运行区，不进入 Git

## 4 浏览器与接口

- 工作台默认语言为中文
- 顶部语言按钮可以切换到英文并恢复中文
- 素材库、场景、分镜、检查器和生成主路径会随语言切换
- 后端健康接口返回 `profile=local-h3` 与 `locked_mode=false`
- 驱动接口只返回 FLUX.2 Klein 图片驱动与 MiniMax H3 视频驱动
- 音频云驱动列表为空

## 5 真实 GPU 生成

FLUX.2 Klein 首帧实测包括：

- 512×512、20 步、随机种子 `408015`
- 生成耗时约 17.1 秒
- 输出大小 `378441` 字节
- 另生成 640×384 宽屏首帧，用于 H3 图生视频

MiniMax H3 冒烟测试包括：

- 416×256、24 FPS、约 5.17 秒
- 生成耗时约 81 秒
- 峰值显存约 12.8GB

MiniMax H3 完整草稿实测包括：

- 608×352、24 FPS、360 帧
- 精确时长 `15.000000` 秒
- H.264 视频与 48kHz AAC 立体声音频
- 输出大小 `1780166` 字节
- 生成耗时约 5 分 55 秒
- 峰值显存约 15.5GB
- SHA-256 `D6F0DFB9D88451EDA4A2EACD30017F75AC041207DC6164C7D6555C4803452EAB`

运行期间遵守先到先用策略，检测到其他 GPU 工作时等待其自然结束，没有终止翻译器或其他 CUDA 进程

## 6 智能抽帧

完整 H3 草稿完成了全片候选采样、质量评分和时间去重：

- 作业编号 `9c938ca9152a`
- 最终选择 `8` 张候选帧
- 第一候选综合得分 `1169.271`
- 第一候选清晰度得分 `1296.176`
- 人物、红色服装、雨夜站台与列车元素在抽样画面中保持连续

## 7 SeedVR2 2× 母版

先使用 48 帧、2 秒片段验证时间分块和交付链路：

- 输入 608×352，输出 1216×704
- 24 FPS、48 帧、精确 2 秒
- H.264 视频与 48kHz AAC 立体声音频
- 输出大小 `932969` 字节
- SHA-256 `6A1EAB00A8F140C62354916240E3183C38EF18D9B73A511217EB991799000944`

随后对完整 15 秒 H3 草稿执行 2× 超分：

- 作业编号 `196dcb74b8fb46cead7101164cf51914`
- 输出 1216×704、24 FPS、360 帧
- 精确时长 `15.000000` 秒
- H.264 视频与 48kHz AAC 立体声音频
- 输出大小 `6209963` 字节
- 平均音量约 `-14.0dB`，最大音量约 `-2.6dB`
- SHA-256 `97CB1506F9781F7A66A95901051AA3C30F247CEB87E59F3B1ED020C5EA3F71DD`
- 总耗时约 2 小时 32 分
- 峰值显存约 15.8GB，最低可用显存约 252MB

自动时间分块为 `25` 帧，随后执行平铺 VAE 解码

在 1 秒、7.5 秒和 13.5 秒各取一帧验收，人物身份、红色服装、列车、蓝橙雨夜光线与镜头推进保持连续，没有发现时长截断

完整 15 秒全片路径已经证明 16GB 显存可以运行，但单次耗时较长

生产使用建议按镜头或短片段执行 SeedVR2，再通过本项目的标准化与拼接链路生成全片母版

## 8 发布与远程链路

GitHub 发布已经完成：

- 公开仓库 `AIALRA-0/AIALRA-MINIMAX-H3`
- 发布候选为独立干净根提交，不携带私有分支或浅克隆缺失历史
- 发布候选工作区和完整提交历史的 Gitleaks 结果均为 `no leaks found`
- 中英文 README 仓库级审计为 `0 error`、`0 warning`
- 前端镜像、后端镜像和 Compose 冒烟测试全部通过
- Compose 冒烟测试验证双服务健康状态与前端到后端的同源代理

VPS 回环链路已经完成：

- 使用反向 SSH 隧道把本机 `127.0.0.1:3000` 连接到 VPS `127.0.0.1:14280`
- VPS 回环请求返回 HTTP 200
- 本机后端运行在 `local-h3` 与锁定模式
- ComfyUI 和 FastAPI 没有直接暴露到公网

仍待确认最终公网主机名，再把 Nginx 路由接入 VPS 现有身份网关并执行匿名拦截与登录后生成验收

用户给出的目标域名与 VPS 当前已配置域名后缀不一致，因此没有猜测或占用公开域名
