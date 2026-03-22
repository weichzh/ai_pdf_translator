import os
from ebooklib import epub  # type: ignore
from typing import List

class EpubBuilder:
    """
    将生成的HTML片段组装成EPUB格式的构建器。
    """
    def __init__(self, title: str, author: str = "AI PDF Translator"):
        """
        初始化EPUB构建器。
        
        Args:
            title (str): 电子书的标题
            author (str): 电子书的作者
        """
        self.book = epub.EpubBook()
        self.book.set_identifier(title.lower().replace(" ", "_"))
        self.book.set_title(title)
        self.book.set_language('zh')
        self.book.add_author(author)
        
        self.chapters: List[epub.EpubHtml] = []
        
        # 添加基本样式
        self.style = '''
BODY { text-align: justify; padding: 0; margin: 0; }
IMG { max-width: 100%; height: auto; }
TABLE { width: 100%; border-collapse: collapse; }
TD, TH { border: 1px solid #ccc; padding: 5px; }
        '''
        default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=self.style)
        self.book.add_item(default_css)
        self.default_css = default_css
        
    def add_chapter(self, title: str, html_content: str, file_name: str) -> None:
        """
        添加一个新的章节（一页或者多页组合）到EPUB中。
        
        Args:
            title (str): 章节标题
            html_content (str): HTML内容 (只需body内容即可)
            file_name (str): 在epub内的文件名，如 'page_1.xhtml'
        """
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang='zh')
        
        # 包装基础结构
        full_html = f"<html><head><title>{title}</title></head><body>{html_content}</body></html>"
        chapter.content = full_html
        chapter.add_item(self.default_css)
        
        self.book.add_item(chapter)
        self.chapters.append(chapter)
        
    def add_image(self, image_path: str, filename_in_epub: str) -> None:
        """
        将本地图片添加到EPUB中。
        
        Args:
            image_path (str): 本地图片的路径
            filename_in_epub (str): 存储在epub内的路径，例如 'images/img_1.png'
        """
        if not os.path.exists(image_path):
            return
            
        with open(image_path, 'rb') as f:
            content = f.read()
            
        image_item = epub.EpubItem(uid=filename_in_epub, file_name=filename_in_epub, media_type="image/png", content=content)
        self.book.add_item(image_item)

    def write_epub(self, output_path: str) -> None:
        """
        将构建的EPUB输出到指定文件。
        
        Args:
            output_path (str): 保存EPUB的输出路径
        """
        # 定义目录结构
        self.book.toc = tuple(self.chapters)
        
        # 添加导航文件
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        
        # 定义书脊排列顺序
        spine = ['nav'] + self.chapters
        self.book.spine = spine
        
        epub.write_epub(output_path, self.book, {})
