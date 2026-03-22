# AI PDF to EPUB Translator

这是一个使用先进大语言模型（LLMs）将 PDF 文件智能转换为支持移动端排版的高质量 EPUB 电子书的自动化脚本。

本项目解决了传统 PDF 转换工具常见的“排版错乱”、“多栏无法阅读”以及“图片/表格丢失”的问题。通过引入多模态大模型的视觉理解能力以及精确的底层 PDF 解析技术，为您带来极其舒适的手机端流式阅读体验。

## ✨ 核心特性

- **🤖 智能 PDF 类型探测**：自动识别 PDF 是纯图片扫描件还是内嵌文本的高质量文档，并在底层动态切换最优策略。
- **📸 完美图片提取**：
  - 对于**文字型 PDF**，直接通过 PyMuPDF 底层无损提取原生图片，百分百零遗漏。
  - 对于**图片扫描型 PDF**，利用强大的多模态大模型（Vision）进行版面分析，精确定位需要单独裁剪保留的图片或复杂表格，防止强制 OCR 导致的乱码与错位。
- **📱 移动端阅读优化 (Mobile-First)**：提示词专门针对手机阅读进行了深度调优。模型会主动拆解多栏排版（Multi-column），修复强制换行的断句，并将内容重整为自然的、单栏的流式网页布局，彻底抛弃死板的固定宽高。
- **⚙️ 健壮的 API 工程设计**：
  - 基于 [LiteLLM](https://github.com/BerriAI/litellm) 统一包装请求，支持无缝切换 OpenAI、Anthropic、甚至本地部署模型或国内（如 SiliconFlow）的各类提供商接口。
  - 内置 API 重试（Retry）功能与可调的防限流间隔（Sleep Interval），保证长篇书籍处理不中断。
- **👀 过程实时预览**：每转换好一页，均会即时本地生成单页 HTML 预览文件，方便您在此过程中核对效果。

## 📦 安装说明

本项目统一采用 [uv](https://github.com/astral-sh/uv) 进行 Python 依赖和环境管理，为您提供极速的体验。

1. **安装 uv (如果您尚未安装)**
   ```bash
   pip install uv
   # 或者使用官方一键安装卷轴
   # curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **克隆/进入项目目录**
   ```bash
   cd ai_pdf_translator
   ```
3. **初始化与同步依赖** (uv 会自动建立虚拟环境并安装好所有需要的包)
   ```bash
   uv sync
   ```

## 🛠️ 配置说明

在运行此程序前，您需要配置大语言模型的相关参数。本项目依赖于 `config.json` 文件。
目录下提供了一个包含配置样例的文件（您可以参考它来创建或直接修改）：

```json
{
    "llm": {
        "provider": "openai",
        "model": "Qwen/Qwen2-VL-72B-Instruct",
        "api_key": "您的_API_KEY",
        "api_base": "https://api.siliconflow.cn/v1"
    },
    "output": {
        "images_dir": "output/images",
        "epub_dir": "output"
    },
    "sleep_interval": 10
}
```

> **注意：** 该脚本强烈依赖于大模型的**视觉多模态 (Vision)** 能力，以及**结构化 JSON 输出能力**。请务必配置诸如 `gpt-5`, `claude-4`, 或者开源的顶级视觉模型如 `Qwen3.5-Plus` 等。请不要使用纯文本大模型，否则服务将会报错！

## 🚀 快速开始

所有的操作都可以通过一条简单的 CLI 命令完成：

```bash
uv run main.py path/to/your/document.pdf --config config.json
```

**运行过程说明：**
1. 脚本将自动在项目目录下创建 `output/` 作为工作输出空间。
2. 运行期间，在 `output/pages/` 目录下会实时生成排版好的单页 HTML，您可以直接双击通过浏览器查看。
3. 从 PDF 中扣出的内嵌图片亦被存储在 `output/images/` 中。
4. 运行结束后，在 `output/` 根目录将生成以源文件命名的标准 `.epub` 书籍。

## 🧩 目录结构

- `main.py`: 主应用入口
- `ai_pdf_translator/pdf_parser.py`: PDF 探测、高斯渲染、字眼提取以及原生图片抓取核心逻辑的封装。
- `ai_pdf_translator/llm_processor.py`: LLM 提示词组装、多模态推断调用与 Pydantic Schema 解析。
- `ai_pdf_translator/epub_builder.py`: 将逐页 HTML + 本地映射图片自动转换为结构化 Epub 归档文档的封装类。
- `config.json`: 模型及系统工作参数设定。
