import fitz  # type: ignore # PyMuPDF
from PIL import Image
from typing import Tuple, Generator, Optional, List, Dict
import io

def detect_pdf_type(pdf_path: str, sample_pages: int = 5) -> str:
    """
    识别PDF的类型是图片型还是文字型。
    通过提取前几页的文本，计算平均每页的文本长度。如果长度极低，则判定为图片型，否则为文字型。
    
    Args:
        pdf_path (str): PDF文件的路径
        sample_pages (int): 采样的页数
        
    Returns:
        str: "image_based" 或 "text_based"
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages_to_check = min(total_pages, sample_pages)
    
    total_text_len = 0
    for i in range(pages_to_check):
        page = doc.load_page(i)
        text = page.get_text()
        total_text_len += len(text.strip())
        
    doc.close()
    
    # 启发式规则：如果前几页平均每页的字符数少于50个，我们认为它是纯图像扫描版PDF
    avg_text_len = total_text_len / pages_to_check if pages_to_check > 0 else 0
    
    if avg_text_len < 50:
        return "image_based"
    return "text_based"

def parse_pdf_pages(pdf_path: str, zoom_factor: float = 2.0) -> Generator[Tuple[int, Image.Image, str, List[Dict]], None, None]:
    """
    解析PDF的每一页，将其渲染为高质量图片，提取该页的原始文本，以及该页内嵌的所有原生图片。
    
    Args:
        pdf_path (str): PDF文件的路径
        zoom_factor (float): 渲染图片时的缩放倍数，越高图片越清晰，但处理越慢
        
    Yields:
        Tuple[int, Image.Image, str, List[Dict]]: 返回页码(从1开始)，该页的Pillow Image对象，提取的文本，以及提取到的原生图片列表(如无则为空)。
    """
    doc = fitz.open(pdf_path)
    
    # 提高渲染分辨率
    mat = fitz.Matrix(zoom_factor, zoom_factor)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # 1. 渲染图片
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        # 2. 提取文本
        text = page.get_text()
        
        # 3. 提取原生图片
        extracted_images = []
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            if base_image:
                extracted_images.append({
                    "id": f"native_img_{img_idx}",
                    "bytes": base_image["image"],
                    "ext": base_image["ext"]
                })
        
        yield page_num + 1, image, text, extracted_images
        
    doc.close()

def crop_image(image: Image.Image, bbox: Tuple[int, int, int, int]) -> Image.Image:
    """
    根据给定的边界框裁剪图片。
    
    Args:
        image (Image.Image): 原始Pillow Image对象
        bbox (Tuple[int, int, int, int]): 格式为 (x, y, width, height) 的边界框坐标
        
    Returns:
        Image.Image: 裁剪后的Pillow Image对象
    """
    x, y, w, h = bbox
    return image.crop((x, y, x + w, y + h))
