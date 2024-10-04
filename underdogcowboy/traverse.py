import os
import base64
import mimetypes

class FileContentProcessor:
    def __init__(self):
        self.NORMAL, self.FILE_PATH = 0, 1
        self.valid_extensions = {'.txt', '.md', '.jpg', '.jpeg', '.png', '.gif'}

    def process_input(self, input_text):
        state = self.NORMAL
        text_buffer = ''
        file_buffer = ''
        output = {'role': 'user', 'parts': []}

        def add_text_part():
            text = ' '.join(text_buffer.split()).strip()
            if text:
                if output['parts'] and isinstance(output['parts'][-1], dict) and 'text' in output['parts'][-1]:
                    output['parts'][-1]['text'] += ' ' + text
                else:
                    output['parts'].append({'text': text})

        def process_file_or_folder(path):
            if os.path.isfile(path):
                add_file_part(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if any(file_path.lower().endswith(ext) for ext in self.valid_extensions):
                            add_file_part(file_path)

        def add_file_part(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                if mime_type.startswith('text'):
                    with open(file_path, 'r') as file:
                        content = file.read()
                    output['parts'].append({'text': f"Content of {file_path}:\n{content}"})
                elif mime_type.startswith('image'):
                    with open(file_path, 'rb') as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    output['parts'].append({
                        'image': {
                            'type': 'base64',
                            'media_type': mime_type,
                            'data': encoded_string
                        }
                    })

        i = 0
        while i < len(input_text):
            if state == self.NORMAL:
                if input_text[i] == '/':
                    add_text_part()
                    text_buffer = ''
                    file_buffer = '/'
                    state = self.FILE_PATH
                else:
                    text_buffer += input_text[i]
            elif state == self.FILE_PATH:
                if input_text[i].isspace():
                    process_file_or_folder(file_buffer)
                    file_buffer = ''
                    state = self.NORMAL
                else:
                    file_buffer += input_text[i]
            i += 1

        if file_buffer:
            process_file_or_folder(file_buffer)
        add_text_part()

        return output

# Example usage
processor = FileContentProcessor()
user_input = "Please analyze the files in /path/to/folder and the image at /path/to/image.jpg"
processed_content = processor.process_input(user_input)
print(processed_content)