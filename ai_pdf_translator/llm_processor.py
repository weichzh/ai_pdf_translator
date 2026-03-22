import base64
import io
import json
from typing import List, Tuple
from PIL import Image
from pydantic import BaseModel, Field
from litellm import completion


class ElementBBox(BaseModel):
    """
    表示页面中的特殊元素边界框。
    """

    element_type: str = Field(..., description="元素类型，例如 'image' 或 'table'")
    bbox: Tuple[int, int, int, int] = Field(
        ..., description="边界框坐标，格式为 (x, y, width, height)"
    )
    need_crop: bool = Field(
        ..., description="是否需要通过裁剪该图片并单独插入 HTML 中以防渲染错误"
    )
    placeholder_id: str = Field(
        ..., description="在生成的 HTML 中用于替换的占位符 ID，例如 'element_001'"
    )


class PageAnalysisResult(BaseModel):
    """
    页面分析的结构化输出。
    """

    elements: List[ElementBBox] = Field(
        default_factory=list, description="页面中需要特殊处理的元素列表"
    )


class LLMProcessor:
    """
    使用 LLM 处理图片和文本的处理器。
    """

    def _parse_model_config(self, sub_config: dict) -> dict:
        api_base = sub_config.get("api_base")
        return {
            "model_name": f"{sub_config.get('provider', 'openai')}/{sub_config.get('model', 'gpt-4o')}",
            "api_key": sub_config.get("api_key"),
            "api_base": None if api_base == "" else api_base,
        }

    def __init__(self, config: dict, no_think: bool = False):
        """
        初始化 LLM 处理器。

        Args:
            config (dict): 包含模型配置信息的字典，支持统一配置或为 analyzer/converter 单独配置。
            no_think (bool): 是否要求模型不要输出思考过程。
        """
        self.no_think = no_think
        # 如果提供了特定 agent 的配置则使用，否则向后兼容回退到统一的 llm 配置
        self.analyzer_conf = self._parse_model_config(config.get("analyzer", config))
        self.converter_conf = self._parse_model_config(config.get("converter", config))

    def _encode_image(self, image: Image.Image) -> str:
        """
        将图片转换为 base64 字符串。
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
        
    def _clean_content(self, content: str) -> str:
        """剥离可能存在的 <think>...</think> 标签，以适应如 DeepSeek 等包含隐藏思考流的模型。"""
        if content and "<think>" in content and "</think>" in content:
            content = content.split("</think>")[-1]
        elif content and "</think>" in content: # 以防万一有些模型前置 think 标签丢失
            content = content.split("</think>")[-1]
        return content.strip()

    def analyze_page_elements(self, image: Image.Image) -> PageAnalysisResult:
        """
        分析页面图片，找出需要特殊处理的图片、表格等，并决定是否裁剪。

        Args:
            image (Image.Image): 页面图片

        Returns:
            PageAnalysisResult: 包含边界框和占位符信息的结构化结果
        """
        base64_image = self._encode_image(image)

        # 因为 litellm 某些模型支持 response_format 为 pydantic，此处我们利用 Instructor 或者强系统提示加 JSON mode
        # 为了兼容性，我们通过系统提示要求输出 JSON，并自己解析，但更健壮的是用 response_format

        system_prompt = f"""
        你是一个专业的排版分析专家。你的任务是仔细扫描整张文档图像，找出所有【插图、照片、图表、复杂表格】在转换纯文本 HTML 时无法直接用文本表达或容易出错的内容。对于转换纯文本 HTML 后不会有阅读问题的元素，不进行标记。
        
        你正在分析的图像精确像素尺寸为：【宽 {image.width} 像素，高 {image.height} 像素】。
        
        请务必且仅仅输出合法的 JSON 格式。返回的 JSON 必须严格遵循以下结构：
        {{
          "elements": [
            {{
              "element_type": "image",
              "bbox": [x, y, w, h],
              "need_crop": true,
              "placeholder_id": "img_1"
            }}
          ]
        }}
        
        字段说明：
        - element_type: 'image' 或 'table' 等。
        - bbox: 包含四个整数的数组 [X, Y, W, H]，X 和 Y 是元素左上角的像素坐标，W 是像素宽度，H 是像素高度。请必须控制坐标在 0 到宽/高 之间。
        - need_crop: 遇到真正的图片或复杂表格时必须为 true。
        - placeholder_id: 唯一标识符，如 img_1 或 table_2。
        """
        
        completion_kwargs = {
            "model": self.analyzer_conf["model_name"],
            "api_key": self.analyzer_conf["api_key"],
            "api_base": self.analyzer_conf["api_base"],
            "messages": [
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "num_retries": 3,
        }
        if self.no_think:
            completion_kwargs["extra_body"] = {"enable_thinking": False}

        try:
            response = completion(**completion_kwargs)
            content = response.choices[0].message.content
            content = self._clean_content(content)
            # 解析纯 JSON 并验证
            data = json.loads(content)
            return PageAnalysisResult.model_validate(data)
        except Exception as e:
            # Fallback 或者打印错误 (在简单实现中返回空)
            print(f"分析页面元素失败: {e}")
            return PageAnalysisResult(elements=[])

    def convert_image_to_html(
        self, image: Image.Image, placeholders: List[ElementBBox]
    ) -> str:
        """
        将纯图片型页面的图片转换为 HTML。

        Args:
            image (Image.Image): 页面图片
            placeholders (List[ElementBBox]): 已经预先挖空或需要插入占位符的元素列表

        Returns:
            str: 转换出的 HTML 内容（只需 body 内部）
        """
        base64_image = self._encode_image(image)
        placeholder_texts = ", ".join(
            [f"{p.placeholder_id} ({p.element_type})" for p in placeholders]
        )

        system_prompt = f"""
        你是一个精通 EPUB 电子书制作和排版的专家。我将提供一张页面扫描图像。
        你的任务是将整个页面的所有文字、段落、标题转化为语义化的 HTML 代码。
        【极度重要】：这些 HTML 将最终打包在 EPUB 格式中，在手机（如 iPhone）等移动设备的屏幕上进行阅读！
        要求：
        1. 【流式排版】：抛弃原图中多列并排或者固定大小的复杂布局结构，将所有段落排布成手机上易于阅读的单栏从上到下的流式阅读流。去除非语义的回车和由于排版换行的断字。
        2. 【语义化标签】：只输出 <body> 内部的 HTML，无需外层标签。使用标准的 <h1>, <h2>, <p>, <blockquote>, 不要硬编码字体大小 (font-size) 或任何固定尺寸。
        3. 【处理占位符】：图中有以下必须特殊保留的元素占位符：{placeholder_texts}。如果你在整理文字时觉得这是放置该图片最连贯的位置，请直接插入以 placeholder_id 作为 id 的 <div> 或 <img> 占位标签，例如 <div id="img_1"></div>。
        4. 不要尝试用文字重新绘制复杂的图片或表格，直接使用占位符代替即可。
        """
        
        completion_kwargs = {
            "model": self.converter_conf["model_name"],
            "api_key": self.converter_conf["api_key"],
            "api_base": self.converter_conf["api_base"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        }
                    ],
                },
            ],
            "num_retries": 3,
        }
        if self.no_think:
            completion_kwargs["extra_body"] = {"enable_thinking": False}

        # 针对长文本和大窗口，使用正常 completion
        response = completion(**completion_kwargs)
        content = response.choices[0].message.content
        return self._clean_content(content).strip(" \n`html")

    def convert_image_and_text_to_html(
        self, image: Image.Image, extracted_text: str, placeholders: List[ElementBBox]
    ) -> str:
        """
        将文字型页面的图片和提取出的文本结合转换/修正为 HTML。

        Args:
            image (Image.Image): 页面图片
            extracted_text (str): 提取出的原始文本
            placeholders (List[ElementBBox]): 已经预先挖空或需要插入占位符的元素列表

        Returns:
            str: 转换出的 HTML 内容（只需 body 内部）
        """
        base64_image = self._encode_image(image)
        placeholder_texts = ", ".join(
            [f"{p.placeholder_id} ({p.element_type})" for p in placeholders]
        )

        system_prompt = f"""
        你是一个精通 EPUB 电子书制作的专家。我将提供一张页面的图像，以及该页提取出的原始文本。
        由于原始文本可能缺乏格式或者换行错乱（尤其是双栏变单栏时），你的任务是：
        结合视觉图像，对提取出的文本进行整理和修正，最终输出一段适合在“手机屏幕”上进行 EPUB 流式阅读的完美 HTML。
        
        【极度重要要求】：
        1. 【单栏流式排版】：不论原图是不是分两栏、三栏或者图文混排，你必须把文字连贯成单栏从上到下的顺序，绝对不要试图使用 CSS 的 absolute 定位或强制写死宽度、外边距。
        2. 【去除硬换行】：修复那些被强制回车打断在句子一半的段落，把它们合并成自然的长段落。
        3. 【语义化标签】：仅输出 <body> 内部的 HTML。规范使用 <h3> 到 <h6>, <p>, <ul>。
        4. 【插入占位符】：对于以下原图里自带的重要图片元素占位符：{placeholder_texts}，请寻找句子间最合理的语意衔接处直接插入：<div id="native_img_0"></div>。请不要尝试去自己用文本拼出图片内容！
        """
        
        completion_kwargs = {
            "model": self.converter_conf["model_name"],
            "api_key": self.converter_conf["api_key"],
            "api_base": self.converter_conf["api_base"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"下面是提取出的原始杂乱文本：\n{extracted_text}\n\n请参考下方的原始图像将其转化为结构良好的 HTML：",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            "num_retries": 3,
        }
        if self.no_think:
            completion_kwargs["extra_body"] = {"enable_thinking": False}

        response = completion(**completion_kwargs)
        # 清理可能存在的 markdown code block 标记和 think 标签
        content = response.choices[0].message.content
        content = self._clean_content(content).strip()
        if content.startswith("```html"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
