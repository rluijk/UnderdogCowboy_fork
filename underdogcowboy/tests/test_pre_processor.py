import pytest
from ..core.markdown_pre_processor import GoogleDocsMarkdownPreprocessor

@pytest.fixture
def preprocessor():
    return GoogleDocsMarkdownPreprocessor()

@pytest.mark.preprocessor
def test_basic_image_replacement(preprocessor):
    markdown = """
    Here's an image: ![][image1]
    [image1]: <data:image/png;base64,BASE64DATA1>
    """
    expected = "Here's an image: data:image/png;base64,BASE64DATA1"
    assert preprocessor.preprocess(markdown).strip() == expected

@pytest.mark.preprocessor
def test_multiple_images(preprocessor):
    markdown = """
    First image: ![][image1]
    Second image: ![][image2]
    [image1]: <data:image/png;base64,BASE64DATA1>
    [image2]: <data:image/jpeg;base64,BASE64DATA2>
    """
    expected = """
    First image: data:image/png;base64,BASE64DATA1
    Second image: data:image/jpeg;base64,BASE64DATA2
    """.strip()
    assert preprocessor.preprocess(markdown).strip() == expected

@pytest.mark.preprocessor
def test_image_reference_without_definition(preprocessor):
    markdown = "Missing image: ![][image1]"
    assert preprocessor.preprocess(markdown).strip() == markdown.strip()

@pytest.mark.preprocessor
def test_image_definition_without_reference(preprocessor):
    markdown = """
    No image reference here.
    [image1]: <data:image/png;base64,BASE64DATA1>
    """
    expected = "No image reference here."
    assert preprocessor.preprocess(markdown).strip() == expected

@pytest.mark.preprocessor
def test_mixed_content(preprocessor):
    markdown = """
    Text before ![][image1] and after.
    More text ![][image2] here.
    [image1]: <data:image/png;base64,BASE64DATA1>
    [image2]: <data:image/jpeg;base64,BASE64DATA2>
    """
    expected = """
    Text before data:image/png;base64,BASE64DATA1 and after.
    More text data:image/jpeg;base64,BASE64DATA2 here.
    """.strip()
    assert preprocessor.preprocess(markdown).strip() == expected

@pytest.mark.preprocessor
def test_preserve_other_markdown_elements(preprocessor):
    markdown = """
    # Heading
    
    - List item 1
    - List item 2 ![][image1]
    
    **Bold text** and *italic text*
    
    [image1]: <data:image/png;base64,BASE64DATA1>
    """
    expected = """
    # Heading
    
    - List item 1
    - List item 2 data:image/png;base64,BASE64DATA1
    
    **Bold text** and *italic text*
    """.strip()
    assert preprocessor.preprocess(markdown).strip() == expected

@pytest.mark.preprocessor
def test_empty_input(preprocessor):
    assert preprocessor.preprocess("") == ""

@pytest.mark.preprocessor
def test_input_with_only_image_definitions(preprocessor):
    markdown = """
    [image1]: <data:image/png;base64,BASE64DATA1>
    [image2]: <data:image/jpeg;base64,BASE64DATA2>
    """
    assert preprocessor.preprocess(markdown).strip() == ""