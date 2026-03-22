import argparse
import json
import os
import re
import time
from pathlib import Path

from ai_pdf_translator.pdf_parser import detect_pdf_type, parse_pdf_pages, crop_image
from ai_pdf_translator.llm_processor import LLMProcessor, ElementBBox
from ai_pdf_translator.epub_builder import EpubBuilder

def load_config(config_path: str) -> dict:
    """加载配置文件。"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"未找到配置文件: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_pdf(pdf_path: str, config_path: str = "config.json") -> None:
    """
    处理整个 PDF 到 EPUB 的转换流程。
    
    Args:
        pdf_path (str): PDF 文件的路径
        config_path (str): 配置文件路径
    """
    config = load_config(config_path)
    
    # 获取相关配置
    sleep_interval = config.get("sleep_interval", 10) # 默认每页间隔10秒，避免频繁请求
    
    # 建立输出目录
    output_dir = config.get("output", {}).get("epub_dir", "output")
    images_dir = config.get("output", {}).get("images_dir", "output/images")
    pages_dir = os.path.join(output_dir, "pages") # 用于随时查看生成的单独页面 HTML
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(pages_dir, exist_ok=True)
    
    # 初始化核心组件
    llm = LLMProcessor(config.get("llm", {}))
    base_name = Path(pdf_path).stem
    builder = EpubBuilder(title=base_name)
    
    print(f"[{base_name}] 开始检测 PDF 类型...")
    pdf_type = detect_pdf_type(pdf_path)
    print(f"[{base_name}] PDF 类型判定为: {pdf_type}")
    
    print(f"[{base_name}] 开始逐页处理并转换为 HTML...")
    for page_num, image, text, extracted_images in parse_pdf_pages(pdf_path, zoom_factor=2.0):
        print(f"[{base_name}] 正在分析第 {page_num} 页元素...")
        
        placeholders = []
        html_replacements = {}
        
        if pdf_type == "image_based":
            # 1. 寻找特殊元素 (图片、复杂表格) - 依赖大模型视觉能力
            analysis = llm.analyze_page_elements(image)
            
            # 2. 对需要提取的特殊内容进行裁剪
            for element in analysis.elements:
                if element.need_crop:
                    # 裁剪图片
                    cropped = crop_image(image, element.bbox)
                    img_filename = f"{base_name}_p{page_num}_{element.placeholder_id}.png"
                    img_path = os.path.join(images_dir, img_filename)
                    cropped.save(img_path)
                    
                    # 记录以便加入 epub，及其在 epub 中的相对路径
                    epub_img_path = f"images/{img_filename}"
                    builder.add_image(img_path, epub_img_path)
                    
                    placeholders.append(element)
                    # 准备替换占位符标签的 <img>
                    html_replacements[element.placeholder_id] = f'<img src="{epub_img_path}" alt="{element.element_type}" />'
        
        else:
            # 针对文字型 PDF: 直接从底层提取原生图片，跳过大模型猜位置，做到百分百准确并保留原清晰度
            for img_dict in extracted_images:
                img_id = img_dict["id"]
                img_ext = img_dict["ext"]
                img_bytes = img_dict["bytes"]
                
                img_filename = f"{base_name}_p{page_num}_{img_id}.{img_ext}"
                img_path = os.path.join(images_dir, img_filename)
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                
                epub_img_path = f"images/{img_filename}"
                builder.add_image(img_path, epub_img_path)
                
                # 兼容现有占位符替换流程
                element = ElementBBox(element_type="image", bbox=(0,0,0,0), need_crop=False, placeholder_id=img_id)
                placeholders.append(element)
                html_replacements[img_id] = f'<img src="{epub_img_path}" alt="native image" />'
        
        print(f"[{base_name}] 正在转换第 {page_num} 页排版为 HTML...")
        
        # 3. 转换为主体 HTML
        if pdf_type == "image_based":
            html_content = llm.convert_image_to_html(image, placeholders)
        else: # text_based
            html_content = llm.convert_image_and_text_to_html(image, text, placeholders)
            
        # 4. 后处理替换 HTML 中的占位符为实际图片标签
        for ph_id, img_tag in html_replacements.items():
            # 捕获可能的各类占位符 id，例如 <div id="img_1"></div>
            pattern = re.compile(rf'<[^>]+id=[\'"]{ph_id}[\'"][^>]*>(?:</[^>]+>)?')
            # 使用 sub 进行替换
            html_content = pattern.sub(img_tag, html_content)
            
        # 实时保存每一页的 HTML，以便随时查看生成效果
        page_html_path = os.path.join(pages_dir, f"{base_name}_page_{page_num}.html")
        with open(page_html_path, 'w', encoding='utf-8') as f:
            f.write(f"<html><head><meta charset='utf-8'><title>Page {page_num}</title></head><body>\n")
            f.write(html_content)
            f.write("\n</body></html>")
        print(f"[{base_name}] 第 {page_num} 页 HTML 已保存到: {page_html_path}")
            
        # 5. 添加为 Epub 的一章 (简化为一页一章)
        builder.add_chapter(f"第 {page_num} 页", html_content, f"page_{page_num}.xhtml")
        
        # 增加时间间隔，避免触发 API 频次限制
        print(f"[{base_name}] 等待 {sleep_interval} 秒以避免频次限制...")
        time.sleep(sleep_interval)
        
    # 生成最终 Epub
    output_epub_path = os.path.join(output_dir, f"{base_name}.epub")
    builder.write_epub(output_epub_path)
    print(f"[{base_name}] 转换完成，EPUB 已保存至: {output_epub_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI PDF to EPUB Translator")
    parser.add_argument("pdf_path", type=str, help="输入 PDF 的路径")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")
    args = parser.parse_args()
    
    process_pdf(args.pdf_path, args.config)
