def test_imports():
    """测试基本模块是否能够被导入。"""
    import ai_pdf_translator.pdf_parser
    import ai_pdf_translator.llm_processor
    import ai_pdf_translator.epub_builder
    assert ai_pdf_translator.pdf_parser is not None
    assert ai_pdf_translator.llm_processor is not None
    assert ai_pdf_translator.epub_builder is not None
