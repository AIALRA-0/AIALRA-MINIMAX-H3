<div align="center">

<h1>模型、工作流与社区资源选型</h1>

<p>面向 16GB 显存的质量优先本地链路</p>

</div>

## 1 结论

当前推荐组合为 FLUX.2 Klein 4B、MiniMax H3 FL2VA INT8、官方 8 步 LoRA、SeedVR2 3B INT8、H3 Continuum V3.8 和 MiniMax H3 Prompt Writer

理由包括：

- 模型与基础工作流能够从官方 Hugging Face 或官方源码仓库取得
- INT8 与 NVFP4 版本适合 16GB 显存下的模型分层卸载
- 8 步 H3 路径优先保留质量，4 步路径留给极低显存或快速预览
- SeedVR2 使用自动时间分块、平铺 VAE 和 2× 输出，避免把整段高分辨率视频同时放入显存
- Continuum 把长镜头拆成可审片、可重生成和可恢复的块，不需要一次性重跑整段
- Prompt Writer 可以使用本地 Ollama 或 DirectGGUF，不依赖付费提示词接口

## 2 提供的低配工作流

已检查用户提供的 `minimax_h3 6g显存+16g内存.json`

它的主要策略包括：

- 参考生视频
- 约 0.9 MP 竖屏
- 8 秒时长
- 4 步采样
- 低显存注意力与 10 个头分块
- 前馈网络 4 分块与 4096 阈值
- 额外的 KJNodes 与预览节点

当前仓库吸收了低显存注意力和前馈分块经验，但没有直接照搬

原因包括：

- 本机有 16GB 显存，可以优先使用官方 8 步 LoRA
- 主工作流要求 15 秒，不是 8 秒
- 草稿使用约 0.2 MP，以降低长片段的总计算量
- 原工作流引用了当前未安装的 INT8 视频 VAE 和额外自定义节点
- 原工作流含一个疑似拼写异常的 `PathchSageAttentionKJ` 节点名称

## 3 Civitai MCP 调研

官方 MCP 客户端已经下载到运行区并按 SHA-256 校验

仓库提供以下可复现入口：

```shell
# 安装并核对 Civitai 官方 MCP CLI
pwsh -File .\scripts\Install-CivitaiMcp.ps1

# 查询 MiniMax H3 与 SeedVR2 工作流元数据
pwsh -File .\scripts\Search-Civitai.ps1 -Query 'MiniMax H3 SeedVR2' -Type Workflows -BaseModel 'MiniMax H3' -Limit 20
```

截至 2026-09-15 核对的候选包括：

- MiniMax H3 with SeedVR2 16GB，模型 `2836319`，版本 `3234545`
- Advanced filmmaking，模型 `2834514`，版本 `3233131`
- EZ v4.1，模型 `2831976`，版本 `3276744`
- Ultra fastest 4 step 6GB，模型 `2835250`，版本 `3316392`
- Multishot v2.7，模型 `2833322`，版本 `3271711`
- H3 Continuum v3.8，模型 `2860061`，版本 `3304593`
- MiniMax H3 Prompt Writer，模型 `2863386`，版本 `3317295`
- Cinematic LoRA，模型 `2908686`，版本 `3289775`
- Camera Control LoRA，模型 `2928691`，版本 `3321657`

Civitai MCP 当前暴露搜索、模型、版本和图片元数据工具，没有模型文件下载工具

因此仓库用它做调查与版本核对，不读取浏览器 Cookie，也不把网页会话转换为下载凭据

## 4 已安装社区组件

- KJNodes，提供 H3 的低显存注意力与前馈分块
- VideoHelperSuite，提供视频读取与兼容辅助
- MiniMax H3 Prompt Writer `0.4.6`，MIT 许可
- H3 Continuum `3.8.2`，MIT 许可

Continuum 支持 1 至 16 个分块，项目文档建议每块 5 至 15 秒，可在审片后接受、重试、继续或从持久化状态恢复

它的完整示例还会引用 Spectrum、rgthree、KJNodes 与 ComfyUI-Easy-Use

当前主工作流不安装 Spectrum、rgthree 或 Easy-Use，因为它们不是单段 15 秒和 SeedVR2 母版链路的必要依赖

## 5 未默认安装的资源

- 4 步与 6GB 工作流适合快速验证，不作为质量优先默认值
- 未给出清晰许可或源码仓库的 LoRA 不进入自动安装脚本
- NSFW 风格 LoRA 不进入默认演示或仓库清单，可在确认许可、基础模型兼容和文件哈希后手动放入 `models\loras`
- Ref2VA 权重体积较大，只有需要多图、多视频或音频锁定时才通过 `-IncludeRef2VA` 安装
- 依赖 Triton 的 KJ PatchTritonVAE 不进入 Windows 默认链路

## 6 主要来源

- [ComfyUI MiniMax H3 教程](https://docs.comfy.org/tutorials/video/minimax/minimax-h3)
- [ComfyUI MiniMax H3 模型仓库](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [MiniMax H3 官方仓库](https://github.com/MiniMax-AI/MiniMax-H3)
- [SeedVR2 官方仓库](https://github.com/ByteDance-Seed/SeedVR)
- [ComfyUI SeedVR2 模型仓库](https://huggingface.co/Comfy-Org/SeedVR2)
- [FLUX.2 官方仓库](https://github.com/black-forest-labs/flux2)
- [FLUX.2 Klein Base 4B FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4b-fp8)
- [MiniMax H3 Prompt Writer](https://github.com/duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer)
- [H3 Continuum](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum)
- [Civitai MCP](https://mcp.civitai.com/llms.txt)

候选列表表示已调查，不表示全部候选都已安装或通过本机 GPU 验证
