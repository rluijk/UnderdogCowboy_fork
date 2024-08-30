import re

class MarkdownPreprocessor:
    def __init__(self):
        self.image_definitions = {}

    def preprocess(self, markdown_text):
        """Main method to preprocess the markdown text."""
        self._extract_image_definitions(markdown_text)
        processed_text = self._replace_image_references(markdown_text)
        return self._clean_up_text(processed_text)

    def _extract_image_definitions(self, markdown_text):
        """Extract image definitions from the markdown text."""
        definition_pattern = r'\[image(\d+)\]:\s*<(data:image/[^>]+)>'
        for match in re.finditer(definition_pattern, markdown_text):
            image_number, image_data = match.groups()
            self.image_definitions[image_number] = image_data

    def _replace_image_references(self, markdown_text):
        """Replace image references with their corresponding base64 data."""
        def replace_func(match):
            image_number = match.group(1)
            return self.image_definitions.get(image_number, match.group(0))

        reference_pattern = r'!\[\]\[image(\d+)\]'
        return re.sub(reference_pattern, replace_func, markdown_text)

    def _clean_up_text(self, markdown_text):
        """Remove image definitions from the end of the document."""
        definition_pattern = r'\[image\d+\]:\s*<data:image/[^>]+>'
        cleaned_text = re.sub(definition_pattern, '', markdown_text)
        return cleaned_text.strip()

class GoogleDocsMarkdownPreprocessor(MarkdownPreprocessor):
    """Specific preprocessor for Google Docs markdown format."""
    # This class can be extended with Google Docs specific methods if needed
    pass
