# huiyijiyao

智能会议纪要生成应用 - 基于 Microsoft VibeVoice ASR 模型

## 📁 项目结构

```
.
├── meeting_minutes_app/     # 主应用程序
│   ├── README.md           # 应用详细说明
│   ├── requirements.md     # 需求文档
│   ├── backend/            # FastAPI 后端服务
│   └── frontend/           # Web 前端界面
├── Microsoft-VibeVoice/    # VibeVoice 相关资源
├── LICENSE                 # MIT 许可证
└── README.md               # 本文件
```

## 🚀 快速开始

请访问 [`meeting_minutes_app/README.md`](./meeting_minutes_app/README.md) 查看详细的安装和使用说明。

### 简要步骤

1. **进入应用目录**
   ```bash
   cd meeting_minutes_app/backend
   ```

2. **安装依赖**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **启动服务**
   ```bash
   python app.py
   ```

4. **访问应用**
   打开浏览器访问 `http://localhost:8000` 或前端页面

## ✨ 主要功能

- 🎯 **说话人分离**: 自动识别不同发言人
- ⏱️ **精确时间戳**: 每段发言的起止时间标记
- 🌍 **多语言支持**: 支持 50+ 种语言识别
- 🔖 **热词定制**: 输入专业术语提升识别准确率
- 📊 **智能摘要**: 自动生成会议关键要点和待办事项
- 💾 **多种导出格式**: PDF, Word, Markdown, JSON

## 🛠️ 技术栈

- **AI 模型**: Microsoft VibeVoice ASR-7B
- **后端框架**: FastAPI + PyTorch + Transformers
- **前端**: HTML5 + Tailwind CSS + Vanilla JavaScript
- **音频处理**: FFmpeg + pydub

## ⚠️ 环境要求

- Python 3.9+
- GPU (推荐，需 14GB+ 显存) 或 CPU
- 首次运行会自动下载模型 (~7GB)

## 📄 详细文档

- [应用使用说明](./meeting_minutes_app/README.md)
- [需求文档](./meeting_minutes_app/requirements.md)
- [后端文档](./meeting_minutes_app/backend/README.md)
- [前端文档](./meeting_minutes_app/frontend/README.md)

## 📝 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件

## 🙏 致谢

本项目基于 [Microsoft VibeVoice](https://github.com/microsoft/VibeVoice) 构建。