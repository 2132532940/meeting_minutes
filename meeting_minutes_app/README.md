# Meeting Minutes Web Application

基于 Microsoft VibeVoice ASR 模型的智能会议纪要生成网页应用。

## 📋 项目结构

```
meeting_minutes_app/
├── requirements.md          # 详细需求文档
├── backend/
│   ├── app.py              # FastAPI 后端服务
│   ├── requirements.txt    # Python 依赖
│   └── README.md           # 后端使用说明
├── frontend/
│   ├── index.html          # 单页面应用
│   └── README.md           # 前端使用说明
└── README.md               # 项目总览
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- GPU (推荐，用于加速模型推理)
- Node.js 16+ (可选，仅用于开发)

### 1. 安装依赖

```bash
cd meeting_minutes_app/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 设置模型路径（默认从 HuggingFace 下载）
export MODEL_PATH="microsoft/VibeVoice-ASR"

# 设置设备（cuda/cpu）
export MODEL_DEVICE="cuda"  # 或 "cpu"
```

### 3. 启动后端服务

```bash
python app.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 打开前端页面

直接在浏览器中打开 `frontend/index.html`，或使用本地服务器：

```bash
cd frontend
python -m http.server 3000
```

然后访问 `http://localhost:3000`

## 📖 API 端点

### POST /transcribe

转录音频文件

**请求参数:**
- `file`: 音频文件 (MP3, WAV, M4A, FLAC, OGG, WEBM)
- `context_info` (可选): 专业术语/热词，提升识别准确率
- `max_new_tokens` (可选): 最大生成 token 数，默认 2048

**响应:**
```json
{
  "status": "success",
  "audio_duration": 120.5,
  "segments": [
    {
      "speaker_id": "Speaker 1",
      "start_time": 0.0,
      "end_time": 15.3,
      "text": "大家好，今天我们讨论..."
    }
  ],
  "full_text": "[0.00s - 15.30s] Speaker 1: 大家好...",
  "processing_time": 45.2,
  "model_info": {...}
}
```

### POST /transcribe-and-summarize

转录并生成会议摘要

### GET /health

健康检查

### GET /supported-formats

获取支持的音频格式

## ✨ 功能特性

- 🎯 **说话人分离**: 自动识别不同发言人
- ⏱️ **精确时间戳**: 每段发言的起止时间
- 🌍 **多语言支持**: 支持 50+ 种语言
- 🔖 **热词定制**: 输入专业术语提升准确率
- 📊 **智能摘要**: 自动生成关键要点和待办事项
- 💾 **多种导出**: PDF, Word, Markdown, JSON
- 🌓 **暗黑模式**: 舒适的夜间使用体验
- 📱 **响应式设计**: 适配桌面和移动设备

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI
- **AI 模型**: Microsoft VibeVoice ASR-7B
- **深度学习**: PyTorch, Transformers
- **音频处理**: FFmpeg, pydub

### 前端
- **UI 框架**: Tailwind CSS
- **图标**: Font Awesome
- **原生 JavaScript**: 无需构建工具

## 📊 性能指标

- **识别准确率**: cpWER < 10% (清晰音频)
- **处理速度**: 60 分钟音频 < 5 分钟 (GPU 加速)
- **并发支持**: 通过任务队列处理多个请求

## ⚠️ 注意事项

1. **GPU 显存**: VibeVoice-ASR-7B 需要约 14GB 显存
2. **音频时长**: 单次处理最长 60 分钟
3. **首次运行**: 会自动下载模型 (~7GB)
4. **隐私安全**: 建议本地部署，避免上传敏感数据

## 🔧 高级配置

### 使用 vLLM 加速

```bash
# 安装 vLLM
pip install vllm

# 参考 docs/vibevoice-vllm-asr.md 配置
```

### 量化推理

```python
# 在 app.py 中修改 DTYPE
DTYPE = torch.int8  # INT8 量化
```

### 自定义模型路径

```bash
# 使用本地模型
export MODEL_PATH="/path/to/local/model"
```

## 📝 开发计划

- [ ] 实时流式转录
- [ ] 多说话人命名
- [ ] LLM 增强摘要
- [ ] 用户认证系统
- [ ] 历史会议管理
- [ ] Zoom/Teams 集成

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [Microsoft VibeVoice](https://github.com/microsoft/VibeVoice)
- [Hugging Face Transformers](https://huggingface.co/transformers/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tailwind CSS](https://tailwindcss.com/)
