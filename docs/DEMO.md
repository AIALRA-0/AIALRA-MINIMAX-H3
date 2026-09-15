<div align="center">

<h1>演示脚本与提示词</h1>

<p>使用合成角色和场景验证 15 秒草稿、抽帧与 2× 母版</p>

</div>

## 1 演示目标

演示使用一个不对应真实人物的成年虚构角色，展示单镜头中的稳定外观、可读动作、环境声和缓慢运镜

成品要求包括：

- 15 秒
- 24 FPS
- H.264 视频
- AAC 音频
- 低分辨率 H3 草稿
- 8 张智能排序候选帧
- SeedVR2 2× 母版

## 2 FLUX.2 首帧提示词

```text
cinematic production still, an adult fictional astronomer in her thirties wearing a dark teal field jacket, standing inside a rain-soaked glass observatory at night, warm practical desk lamps, large brass telescope, distant city lights reflected on wet glass, realistic skin texture, restrained color grade, 35 mm lens, medium wide composition, natural posture, no text, no watermark
```

## 3 MiniMax H3 15 秒提示词

```text
A single continuous cinematic shot inside a rain-soaked glass observatory at night. An adult fictional astronomer in her thirties wears a dark teal field jacket beside a large brass telescope. She studies a handwritten star chart, slowly looks up as a meteor crosses the sky, then turns the telescope toward it. The camera begins in a steady medium-wide frame, performs a slow controlled dolly-in, and ends on her focused expression reflected in the wet glass. Warm desk lamps contrast with cool blue city light. Natural body motion, stable identity and wardrobe, realistic wet reflections, restrained film grain. Soft rain on glass, quiet room tone, subtle paper movement, distant thunder, no music, no subtitles, no on-screen text.
```

## 4 竖屏短剧变体

```text
A 15-second vertical cinematic drama shot. In a quiet late-night train carriage, an adult fictional courier in a charcoal coat notices a sealed red envelope on the empty seat opposite. She hesitates, reaches for it, then freezes when the carriage lights briefly flicker. Slow push-in, stable face and wardrobe, controlled hand movement, realistic reflections in the window, practical fluorescent lighting mixed with passing city lights. Train ambience, soft rail rhythm, fabric movement, one brief electrical buzz, no music, no subtitles, no text.
```

## 5 验收顺序

- 第一步，固定随机种子并保存原始 H3 输出
- 第二步，确认时长大于或等于 15 秒所需的模型帧数
- 第三步，标准化为精确 15 秒和 24 FPS
- 第四步，抽取 8 张候选帧并查看首选帧是否清晰、曝光正常且人物完整
- 第五步，运行 SeedVR2 2× 母版
- 第六步，对比人物身份、衣着、手部、玻璃反射、镜头运动和音频连续性
- 第七步，把草稿、候选帧清单和母版路径记录到验证文档

不使用真实人物、品牌标志、版权角色或账户数据作为公开演示输入

## 6 已完成演示

最终实测改用雨夜末班车场景，角色仍是不存在的成年虚构人物

完整链路已经生成：

- FLUX.2 Klein 宽屏首帧
- MiniMax H3 608×352、24 FPS、15 秒带声草稿
- 8 张智能排序候选帧
- SeedVR2 1216×704、24 FPS、15 秒带声母版

最终母版保存在运行区：

```text
D:\AIALRA-MINIMAX-H3\outputs\studio\aialra_h3_15s_demo\pipeline\196dcb74b8fb46cead7101164cf51914\seedvr2_delivery.mp4
```

演示镜头从雨夜站台全身构图缓慢推进到中近景，列车由远处驶近并从人物右侧通过

三处抽样画面显示人物身份、红色外套、场景照明和列车方向保持连续

详细编码、时长、音频、哈希和资源占用见 [验证记录](VALIDATION.md)

## 7 质量优先三段式演示

长镜头更容易累积身份和动作漂移，因此新增一个可断点续跑的三段式生成器

它使用本仓库的 H3 结构化提示词，每段约 5.17 秒，上一段尾帧自动成为下一段首帧

```powershell
& '<studio-python>' .\backend\tools\run_h3_demo.py '<anchor-image>' `
  --runtime-root '<runtime-root>' `
  --megapixels 0.4 `
  --steps 20 `
  --ffmpeg '<ffmpeg-full-path>'
```

三段提示词位于：

- [`examples/prompts/h3_glasshouse_shot_01.txt`](../examples/prompts/h3_glasshouse_shot_01.txt)
- [`examples/prompts/h3_glasshouse_shot_02.txt`](../examples/prompts/h3_glasshouse_shot_02.txt)
- [`examples/prompts/h3_glasshouse_shot_03.txt`](../examples/prompts/h3_glasshouse_shot_03.txt)

真实结果为 864×480、24 FPS、372 帧和 15.5007 秒，总 H3 计算约 8 分钟

视频部分使用码流复制，音频在镜头边界做响度统一与 80ms 淡化，最终视频流哈希与原始拼接结果一致

运行区成片：

```text
D:\AIALRA-MINIMAX-H3\outputs\studio\aialra_h3_glasshouse_15s\delivery\aialra_h3_glasshouse_15s.mp4
```
