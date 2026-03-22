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
        "analyzer": {
            "provider": "openai",
            "model": "Qwen/Qwen3.5-27B",
            "api_key": "YOUR_API_KEY_HERE",
            "api_base": "https://api.siliconflow.cn/v1"
        },
        "converter": {
            "provider": "openai",
            "model": "Qwen/Qwen3.5-35B-A3B",
            "api_key": "YOUR_API_KEY_HERE",
            "api_base": "https://api.siliconflow.cn/v1"
        }
    },
    "output": {
        "images_dir": "output/images",
        "epub_dir": "output"
    },
    "sleep_interval": 10
}
```

> **进阶提示 (双阶段 Agent)：**
> 本项目支持根据工作流特性的不同独立配置大模型：
> - **`analyzer`**：用来对扫描件 PDF 页面进行视觉理解、感知识别图片和表格，并提取精准坐标。**此环节强烈依赖于大模型的视觉多模态 (Vision) 能力以及严格输出纯正结构化 JSON 的能力**。务必为其配置顶级视觉模型。目前使用的开源多模态模型如Qwen3.5-27B等存在找不准位置的问题，可以考虑自行优化提示词或者更换模型。
> - **`converter`**：用来将提取出的粗糙长文本结合上下文重新修饰或者直接将图片转化为移动端精美的流式 HTML 结构。此环节一般的视觉模型即可胜任。

## 🚀 快速开始

所有的操作都可以通过一条简单的 CLI 命令完成：

```bash
# 默认基本使用
uv run main.py path/to/your/document.pdf --config config.json

# 最快无图运行
uv run main.py path/to/your/document.pdf --config config.json --skip-images --no-think
```

**命令行控制台高级参数说明：**

- `--skip-images`：跳过耗时的版面底层图片分析及精准图像截图。直接利用大模型将整页纯转换为文本内容，这对于**纯文本类 PDF**或不需要查看插图只在乎获取文本知识信息的场景非常适合，能够成倍提升执行速度。
- `--no-think`：关闭模型的深思慎取过程。当前非常多超高参数的高阶推理模型总会强制产生耗费大量无意义时间的 `<think>分析逻辑</think>`。挂上此标签之后能在与支持它的服务端 API（譬如 `enable_thinking=false`）交互时，实现直接粗暴地甩出最终答案的效果。

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
