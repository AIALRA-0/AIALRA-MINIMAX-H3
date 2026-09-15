<div align="center">

<h1>AIALRA MiniMax H3 Studio</h1>

<p>A local AI drama workstation for an RTX 4080 16GB, from 15-second drafts to 2× masters</p>

<p><strong>Windows local-first · Chinese by default · No paid model APIs · End-to-end validated on an RTX 4080 16GB</strong></p>

<p><a href="README.md">简体中文</a> · <a href="docs/LOCAL_DEPLOYMENT.md">Deployment</a> · <a href="docs/VALIDATION.md">Validation</a> · <a href="docs/RESEARCH.md">Research</a></p>

</div>

## 1 Scope

This repository builds on [AI Movie Studio 2](https://github.com/Heroesjouney/AIMovieStudiov2) and narrows the runtime to a practical Windows configuration with an RTX 4080 16GB and 64GB of system memory

The main path provides:

- FLUX.2 Klein 4B for characters, locations, and starting frames
- MiniMax H3 INT8 with the 8-step LoRA for video drafts up to 15 seconds
- Delivery normalization to 15 seconds, 24 FPS, H.264, and AAC
- Keyframe ranking using sharpness, exposure, edge content, and temporal coverage
- SeedVR2 3B INT8 for a 2× video master
- Shot, take, audio, assembly, and timeline management
- H3 Continuum V3.8 for reviewable chunks, partial reruns, and resumable long-form work
- Three roughly five-second quality shots chained with tail-frame anchors and losslessly assembled for continuity demos

The interface can switch between Chinese and English, with Chinese as the first-run default

## 2 First successful run

The installer keeps models, environments, caches, and outputs in the D-drive runtime area instead of the source repository

```powershell
# Install pinned ComfyUI, community nodes, backend, and frontend dependencies
pwsh -File .\scripts\Install-Local.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'

# Review the model licenses, then download and size-check official Hugging Face files
pwsh -File .\scripts\Download-Models.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3' -AcceptModelTerms

# Start ComfyUI on the loopback interface only
pwsh -File .\scripts\Start-ComfyUI.ps1 -RuntimeRoot 'D:\AIALRA-MINIMAX-H3'

# Start the backend and production frontend
pwsh -File .\scripts\Start-Studio.ps1 `
  -RuntimeRoot 'D:\AIALRA-MINIMAX-H3' `
  -FfmpegPath 'K:\AIALRA-H3-Tools\ffmpeg-full\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe'
```

Open `http://127.0.0.1:3000`. A healthy first run shows the project page in Chinese, a connected status, FLUX.2 Klein as the only image driver, and MiniMax H3 as the only video driver

```powershell
# Show local service health and current GPU memory
pwsh -File .\scripts\Get-LocalStatus.ps1

# Stop only verified processes started for this repository
pwsh -File .\scripts\Stop-Local.ps1
```

See [local deployment](docs/LOCAL_DEPLOYMENT.md) for prerequisites, storage layout, and troubleshooting

## 3 Draft-to-master workflow

- First, create a character, location, or starting frame with FLUX.2 Klein
- Second, select MiniMax H3 and use the 0.2 MP, 8-step, 15-second draft preset
- For a quality-first short, use the 0.4 MP, 20-step base profile in roughly five-second shots and carry each tail frame into the next shot
- Third, rank keyframes and review the eight temporally distributed candidates
- Fourth, approve identity, composition, and motion, then run the SeedVR2 2× master pass
- Fifth, place the normalized 15-second master on the timeline for assembly or export

MiniMax H3 needs most of the GPU. Let translation, language-model, or other CUDA work finish naturally before starting a run

On a dual-GPU machine, every model remains pinned to the RTX 4080. The display RTX 2070 Super is eligible only for fixed-function NVENC when graphics, encode, decode, free-memory, and pixel-rate gates are all safe

Two consecutive threshold violations terminate only the encoder process owned by this project and fall back to CPU. Compatible shots use stream-copy assembly first, which uses neither GPU and introduces no additional compression loss

## 4 Pinned local stack

- ComfyUI `0.35.0` at commit `36da3ff`
- MiniMax H3 FL2VA INT8, Qwen3-VL NVFP4, video VAE, audio VAE, and official 8-step LoRA
- SeedVR2 3B INT8 and FP16 VAE
- FLUX.2 Klein Base 4B FP8, Qwen 3 4B text encoder, and FLUX.2 VAE
- KJNodes, VideoHelperSuite, and MiniMax H3 Prompt Writer
- H3 Continuum `3.8.2` at commit `c38c616`
- The official Civitai MCP for public metadata and version research only
- Windows Triton and SageAttention are installed, while the H3 workflow keeps its validated Comfy Kitchen attention backend until an isolated A/B test supports a change

Model weights are excluded from Git. [`config/model-manifest.json`](config/model-manifest.json) records the source repositories and expected byte counts

## 5 Validation status

Validated on 2026-09-15:

- Backend suite: `19 passed`
- Production frontend build, ESLint, and TypeScript checks passed
- Three ComfyUI API workflows passed validation against a live `object_info` response
- H3 Continuum upstream suite: `1260 passed`, `2 skipped`; one test initially hit Windows GBK decoding and passed when rerun under UTF-8
- The CPU media pipeline converted a 15.2-second fixture to exactly 15.0 seconds, 24 FPS, 360 frames, with AAC audio
- Keyframe ranking produced and stored eight selected frames
- Chinese default rendering and the English toggle passed local browser verification
- A real FLUX.2 Klein 512×512 starting frame completed in about 17 seconds
- A real MiniMax H3 draft completed at 608×352, 24 FPS, and 360 frames in about 5 minutes 55 seconds
- A full SeedVR2 2× master completed at 1216×704, 24 FPS, and 360 frames in about 2 hours 32 minutes
- The new quality demo uses three 0.4 MP, 20-step base-model shots and delivers 864×480, 372 frames, and 15.5007 seconds after about eight minutes of H3 compute
- Tail frames anchor all three shots; video assembly is stream-copy, while native-audio boundaries receive loudness matching and 80 ms fades
- The final master retained exactly 15.000 seconds of H.264 video and AAC stereo audio; sampled frames preserved the character, wardrobe, train, lighting, and camera progression
- Gitleaks reported `no leaks found` for both the publication worktree and its complete commit history
- The [public GitHub repository](https://github.com/AIALRA-0/AIALRA-MINIMAX-H3) is live; the frontend image, backend image, and Compose proxy smoke test all passed
- The VPS loopback reverse tunnel is live and returns HTTP 200 while the local studio runs in locked mode
- Public DNS, TLS, anonymous identity-gateway enforcement, and the AIALRA homepage card passed real browser checks
- The new demo appears in the Chinese project page and plays with a browser-reported duration of 15.5326 seconds

A full 15-second 2× pass is feasible in 16GB of VRAM, but production runs should upscale short shots or segments before assembly to reduce retry and review time

The authenticated session remains under the deployer's account control; public validation did not store or bypass login credentials

See [validation evidence](docs/VALIDATION.md) for commands, artifacts, and limitations

## 6 Storage and migration

The default runtime is `D:\AIALRA-MINIMAX-H3` to reduce pressure on the source drive

The `models`, `cache`, `outputs`, `venvs`, and `ComfyUI` directories are relocatable. Change `-RuntimeRoot` when moving to the final drive

Stop repository services and verify destination capacity and file byte counts before migration. The project does not bulk-delete unknown directories

## 7 Remote-access boundary

ComfyUI, FastAPI, and the frontend bind to `127.0.0.1` by default

The recommended public path uses a reverse tunnel to a VPS, with Authentik providing authentication, sessions, and access policy. Only the gateway-protected frontend should be public

No real domain, SSH host, token, cookie, API key, or Authentik client secret belongs in this repository. See the [VPS and Authentik template](docs/REMOTE_DEPLOYMENT.md)

## 8 Research and community assets

The stack was selected by cross-checking official ComfyUI, Hugging Face, MiniMax, Black Forest Labs, SeedVR2, community-node source code, and Civitai MCP metadata

Workflows with unclear licensing, missing dependencies, or redundant 16GB paths were not installed. See [research and selection](docs/RESEARCH.md) for the Civitai model IDs and low-memory workflow comparison

## 9 License and acknowledgements

This repository retains the upstream [GNU Affero General Public License v3.0](LICENSE)

Hosted modified services must follow the AGPL-3.0 network-source obligations. Model weights, LoRAs, and third-party nodes remain subject to their respective licenses

Thanks to [AI Movie Studio 2](https://github.com/Heroesjouney/AIMovieStudiov2), [ComfyUI](https://github.com/Comfy-Org/ComfyUI), [MiniMax](https://github.com/MiniMax-AI/MiniMax-H3), [SeedVR2](https://github.com/ByteDance-Seed/SeedVR), [Black Forest Labs](https://github.com/black-forest-labs/flux2), and every community maintainer listed in the research notes
