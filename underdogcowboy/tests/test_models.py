import pytest
import requests_mock
import os
import json
from ..core.model import AnthropicModel, VertexAIModel, GroqModel, ModelManager

@pytest.mark.expensive
@pytest.mark.parametrize("model_class, model_id", [
    (AnthropicModel, 'claude-3-5-sonnet-20240620'),
    (VertexAIModel, 'gemini-pro'),
    (GroqModel, 'mixtral-8x7b-32768')
])
@pytest.mark.parametrize("include_system_message", [True, False])
def test_model_generate_content(model_class, model_id, include_system_message):
    model = model_class(model_id)
    
    conversation = []
    if include_system_message:
        if model_class == VertexAIModel:
            conversation.append({'role': 'system', 'parts': [{'text': 'You are a helpful assistant.'}]})
        else:
            conversation.append({'role': 'system', 'content': 'You are a helpful assistant.'})
    
    if model_class == VertexAIModel:
        conversation.append({'role': 'user', 'parts': [{'text': 'Hello'}]})
    else:
        conversation.append({'role': 'user', 'content': 'Hello'})
    
    response = model.generate_content(conversation)
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Error:" not in response
    assert any(word in response.lower() for word in ['hello', 'hi', 'greetings'])

def test_model_manager():
    for model_name in ['anthropic', 'google-vertex', 'groq']:
        model = ModelManager.initialize_model(model_name)
        assert isinstance(model, (AnthropicModel, VertexAIModel, GroqModel))
    
    with pytest.raises(ValueError):
        ModelManager.initialize_model('unsupported_model')

def test_model_manager_with_id():
    model_configs = [
        ('anthropic', 'claude-3-5-sonnet-20240620', AnthropicModel),
        ('google-vertex', 'gemini-pro', VertexAIModel),
        ('groq', 'mixtral-8x7b-32768', GroqModel)
    ]
    
    for provider, model_id, expected_class in model_configs:
        model = ModelManager.initialize_model_with_id(provider, model_id)
        assert isinstance(model, expected_class)
        assert model.model_id == model_id

    with pytest.raises(ValueError):
        ModelManager.initialize_model_with_id('unsupported_provider', 'some_model_id')

@pytest.mark.expensive
@pytest.mark.multimodal
def test_claude_multiple_images_handling():
    model = AnthropicModel('claude-3-5-sonnet-20240620')
    
    # Paths to test images
    image_path1 = os.path.join(os.path.dirname(__file__), 'test_image1.png')
    image_path2 = os.path.join(os.path.dirname(__file__), 'test_image2.png')
    
    # Ensure the test images exist
    assert os.path.exists(image_path1), f"Test image 1 not found at {image_path1}"
    assert os.path.exists(image_path2), f"Test image 2 not found at {image_path2}"
    
    conversation = [
        {'role': 'user', 'parts': [
            {'text': 'Compare these two images:'},
            {'image_url': {'url': image_path1}},
            {'text': 'and'},
            {'image_url': {'url': image_path2}},
            {'text': 'What are the main differences?'}
        ]}
    ]
    
    response = model.generate_content(conversation)
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Error:" not in response
    
@pytest.fixture
def anthropic_model():
    return AnthropicModel("claude-3-5-sonnet-20240620")

@pytest.mark.multimodal
def test_create_conversation_structure(anthropic_model):
    # Test case 1: Text with no images
    text1 = "Hello, how are you?"
    result1 = anthropic_model.create_conversation_structure(text1)
    expected1 = [{'role': 'user', 'parts': [{'text': 'Hello, how are you?'}]}]
    assert result1 == expected1

    # Test case 2: Text with one image
    text2 = "Here's a picture: /path/to/image.jpg"
    result2 = anthropic_model.create_conversation_structure(text2)
    expected2 = [{'role': 'user', 'parts': [
        {'text': "Here's a picture:"},
        {'image_url': {'url': '/path/to/image.jpg'}}
    ]}]
    assert result2 == expected2

    # Test case 3: Text with multiple images and text
    text3 = """This is the first line.
    Here's image 1: /path/to/image1.png
    Some text between images.
    Here's image 2: /path/to/image2.jpg
    This is the last line."""
    result3 = anthropic_model.create_conversation_structure(text3)
    expected3 = [{'role': 'user', 'parts': [
        {'text': "This is the first line. Here's image 1:"},
        {'image_url': {'url': '/path/to/image1.png'}},
        {'text': "Some text between images. Here's image 2:"},
        {'image_url': {'url': '/path/to/image2.jpg'}},
        {'text': 'This is the last line.'}
    ]}]
    assert result3 == expected3

    # Test case 4: Text with image and no surrounding text
    text4 = "/path/to/lonely_image.gif"
    result4 = anthropic_model.create_conversation_structure(text4)
    expected4 = [{'role': 'user', 'parts': [
        {'image_url': {'url': '/path/to/lonely_image.gif'}}
    ]}]
    assert result4 == expected4

    # Test case 5: Text with unsupported image format (should be ignored)
    text5 = "This image should be ignored: /path/to/image.svg"
    result5 = anthropic_model.create_conversation_structure(text5)
    expected5 = [{'role': 'user', 'parts': [
        {'text': 'This image should be ignored: /path/to/image.svg'}
    ]}]
    assert result5 == expected5

     # Test case 6: Text with base64 encoded image
    text6 = "Here's a base64 image: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg== And some text after."
    result6 = anthropic_model.create_conversation_structure(text6)
    expected6 = [{'role': 'user', 'parts': [
        {'text': "Here's a base64 image:"},
        {'image': {'type': 'base64', 'media_type': 'image/png', 'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='}},
        {'text': 'And some text after.'}
    ]}]
    assert result6 == expected6

    # Test case 7: Multiple base64 encoded images
    text7 = "First image: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg== Middle text. Second image: data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAA=="
    result7 = anthropic_model.create_conversation_structure(text7)
    expected7 = [{'role': 'user', 'parts': [
        {'text': "First image:"},
        {'image': {'type': 'base64', 'media_type': 'image/png', 'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='}},
        {'text': 'Middle text. Second image:'},
        {'image': {'type': 'base64', 'media_type': 'image/jpeg', 'data': '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAA=='}}
    ]}]
    assert result7 == expected7

    # Test case 8: Mix of file paths and base64 encoded images
    text8 = "File image: /path/to/image.jpg Then base64: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
    result8 = anthropic_model.create_conversation_structure(text8)
    expected8 = [{'role': 'user', 'parts': [
        {'text': "File image:"},
        {'image_url': {'url': '/path/to/image.jpg'}},
        {'text': 'Then base64:'},
        {'image': {'type': 'base64', 'media_type': 'image/png', 'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='}}
    ]}]
    assert result8 == expected8



@pytest.mark.multimodal
def test_generate_content_with_base64_images(anthropic_model):
    # Mock the API response
    mock_response = {
        "content": [{"text": "I see two images. The first appears to be a small red square. The second appears to be a small blue circle."}]
    }

    # Prepare a conversation with base64 encoded images
    conversation = [{
        'role': 'user',
        'parts': [
            {'text': "Describe these two images:"},
            {'image': {'type': 'base64', 'media_type': 'image/png', 'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='}},
            {'text': "and"},
            {'image': {'type': 'base64', 'media_type': 'image/png', 'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='}}
        ]
    }]

    # Use requests_mock to mock the API call
    with requests_mock.Mocker() as m:
        m.post(anthropic_model.api_url, json=mock_response)

        # Call generate_content
        response = anthropic_model.generate_content(conversation)

        # Check that the response is as expected
        assert response == mock_response['content'][0]['text']

        # Check that the request was made with the correct data
        last_request = m.last_request
        request_body = json.loads(last_request.text)

        # Verify that the images were included in the request
        assert len(request_body['messages']) == 1
        assert len(request_body['messages'][0]['content']) == 4
        assert request_body['messages'][0]['content'][1]['type'] == 'image'
        assert request_body['messages'][0]['content'][1]['source']['type'] == 'base64'
        assert request_body['messages'][0]['content'][3]['type'] == 'image'
        assert request_body['messages'][0]['content'][3]['source']['type'] == 'base64'


@pytest.mark.expensive
@pytest.mark.multimodal
@pytest.mark.real_api
def test_generate_content_with_base64_images_real_api(anthropic_model):
    # Prepare a conversation with base64 encoded images
    # Note: Using a 1x1 pixel transparent PNG for minimal data transfer
    tiny_transparent_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
    
    conversation = [{
        'role': 'user',
        'parts': [
            {'text': "Describe these two images:"},
            {'image': {'type': 'base64', 'media_type': 'image/png', 'data': tiny_transparent_png}},
            {'text': "and"},
            {'image': {'type': 'base64', 'media_type': 'image/png', 'data': tiny_transparent_png}}
        ]
    }]

    # Call generate_content with real API
    response = anthropic_model.generate_content(conversation)

    # Basic checks on the response
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Error:" not in response

    # Check for keywords that suggest the model recognized the images
    expected_keywords = ['image', 'transparent', 'pixel', 'small']
    assert any(keyword in response.lower() for keyword in expected_keywords)

    # Print the response for manual inspection
    print(f"API Response: {response}")