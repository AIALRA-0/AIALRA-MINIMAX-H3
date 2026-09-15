<div align="center">

<h1>验证记录</h1>

<p>记录已执行检查、可复现命令和仍待完成的证据</p>

</div>

## 1 验证环境

- 日期 `2026-09-15`
- GPU `NVIDIA GeForce RTX 4080 16GB`
- 显示 GPU `NVIDIA GeForce RTX 2070 Super 8GB，PCIe 3.0 x1`
- 系统内存 `64GB`
- CPU `Intel Core i9-13900K`
- ComfyUI `0.35.0`
- PyTorch `2.14.0+cu130`
- 前端 Next.js `14.2.35`

## 2 已完成检查

```shell
# 后端单元与集成测试
Push-Location .\backend
& 'D:\AIALRA-MINIMAX-H3\venvs\studio-backend\Scripts\python.exe' -m pytest -q
Pop-Location
```

结果为 `28 passed`

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

## 8 连续性纠错与 H3 Continuum 实测

旧三段式玻璃温室样片没有通过人工观看验收，撤销“质量版”和“无缝”结论：

- 三段由独立 H3 任务生成，`0.25` 秒 xfade 只能模糊像素边界，不能恢复动作相位、镜头速度、视线、姿态和声场语义
- 归一化画面跳变量只反映相邻像素差，不能作为连贯性通过条件
- 旧样片仅保留为失败回归材料，不进入演示或生产默认路径
- 2070 Super 继续只承担桌面显示和受保护的媒体编码，模型任务仍固定在 RTX 4080

当前生产候选改用已安装的 H3 Continuum `3.8.2`：

- `H3ContinuumSamplerV38` 在采样阶段传递上一分块的视频与音频 latent 上下文
- 连贯上下文使用 `Balanced — 22 frames`，音频连续开启，20 步基础模型，不使用 Turbo LoRA
- `H3ContinuumAssembleSeamV35` 只执行精确时长、原生分块装配和已验证的瞬态微闪修正，不使用 xfade
- 736×416 的 2×4 秒功能门耗时 `180.3` 秒，`Analyze Only` 模式下原生边界没有明显硬切
- 1024×576 的 3×5 秒正式候选耗时 `690.5` 秒，输出 24 FPS、360 帧、14.998 秒 H.264 与 AAC
- 5 秒与 10 秒边界的 12 帧抽样未发现构图重置、人物替换、服装跳变或道具瞬移
- 全片抽样显示人物、指南针、温室结构、曝光和色彩保持连续，音频波形没有边界归零重启
- 动作幅度仍偏保守，暗部和皮肤细节尚未达到最终高分辨率终片标准，因此当前结论仅为“连贯性候选通过”

Ref2VA 真实冒烟测试已经完成：

- 下载并校验 20.97GB Ref2VA INT8 主模型与 1.96GB 官方 4 步 Turbo LoRA
- 0.2MP、124 帧、约 5.17 秒，端到端耗时 `100.3` 秒
- 峰值显存约 15.5GB，可在 RTX 4080 16GB 上运行
- 同时输入一张身份图和上一镜视频，上一镜音频作为配套参考进入 Context-IR
- Ref2VA 首帧与上一镜尾帧跳变量为 `0.196514`，因此它适合跨景别身份与场景锁定，不作为零痕迹同机位续帧的默认模式

质量版 FL2VA 对照测试已经完成：

- 0.2MP、20 步、124 帧、约 5.17 秒，端到端耗时 `90.3` 秒
- 与上一镜尾帧的跳变量为 `0.018355`，亮度差为 `0.010489`
- 时间轴真实导出得到 864×480、24 FPS、H.264 与 AAC 成片，时长约 10.1 秒

同机位长镜头改用 H3 Continuum 原生续写，Ref2VA 继续用于允许镜头语言变化的身份与场景参考，两者不再用 xfade 冒充语义连续

运行区结果：

```text
D:\AIALRA-MINIMAX-H3\outputs\continuum\aialra_h3_continuum_gate_v1.mp4
D:\AIALRA-MINIMAX-H3\outputs\continuum\aialra_h3_continuum_quality_candidate_v1.mp4
D:\AIALRA-MINIMAX-H3\outputs\studio\aialra_h3_glasshouse_15s\delivery\ref2va_continuity_smoke_5s.mp4
D:\AIALRA-MINIMAX-H3\outputs\studio\aialra_h3_glasshouse_15s\delivery\fl2va_quality_continuity_joined_10s.mp4
```

最后两项属于对照和失败回归材料，不是质量演示

## 9 发布与远程链路

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

公网接入已经完成：

- DNS A 记录从 Cloudflare 解析到 VPS，公共递归解析器返回一致结果
- Let's Encrypt 证书签发成功，HTTP 自动跳转 HTTPS
- Nginx 只把站点代理到 VPS 回环隧道端口
- 匿名请求返回 `302` 到身份网关登录页
- AIALRA 主页显示 H3 Studio 卡片并指向受保护入口
- 浏览器验证登录页标题、登录按钮与主页卡片均可读取

认证后的会话由部署者账户控制，本次没有保存 Cookie、口令或绕过登录步骤

## 9 双 GPU 调度实测

全部模型 URL 都指向 GPU 0 上的单一 ComfyUI 实例，GPU 1 没有运行 ComfyUI 或模型节点

媒体健康检查检测到显示 GPU 上存在活跃 3D 负载时返回：

- `selected_encoder=libx264`
- `reason=display_gpu_busy`
- NVENC 与 NVDEC 使用率仍为 `0%`

这证明当前前台负载会阻止项目把编码任务放到 2070

媒体管线还通过以下自动化测试：

- 兼容镜头拼接不会调用任何视频编码器
- 超过 1080p30 等效像素率时强制 CPU
- 数值环境变量损坏时安全回到默认值
- FFmpeg 9 使用 `-fps_mode vfr` 完成抽帧

## 10 已撤销的三段式质量样片

以下结果保留为失败回归基线，不属于当前质量演示，玻璃温室样片采用 FLUX.2 首帧与三个独立 MiniMax H3 I2V 镜头：

- 每段 `0.4 MP`、基础模型 `20` 步、随机种子 `408031` 至 `408033`
- 每段 `864×480`、`24 FPS`、`124` 帧、`5.166667` 秒
- 每段生成耗时约 `160.2` 秒，总 H3 计算约 `480.6` 秒
- 三段使用上一段尾帧作为下一段输入锚点
- 成片 `864×480`、`372` 帧、`15.500651` 秒，含 AAC 音频
- 文件大小 `1650464` 字节
- SHA-256 `2AE3ACDB309DCFBF4A6E5C30557582545008460562C59A3A414281A09D9103D6`
- 拼接前后视频流哈希一致，为 `4332868E2F36A652442457787E76EB490F74DAAE76EDE4AA7467C5AC0684953C`
- 音频平均响度约 `-22.4dB`，峰值约 `-1.9dB`
- 全片抽取并排序 `8` 张候选帧

固定时间抽查覆盖 0.5 秒、5.0 秒、5.3 秒、10.2 秒、10.6 秒和 15.0 秒

静态抽样中的人物短发、深色外套和温室色调相近，但完整播放暴露出动作相位、镜头速度和音频边界重启，因此这一结论不能作为连贯性通过依据

成片曾复制到项目视频目录并成功播放，这只证明编码和网页链路可运行，不证明生成质量合格

用户给出的目标域名与 VPS 当前已配置域名后缀不一致，因此没有猜测或占用公开域名
