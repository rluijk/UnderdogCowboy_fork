import pytest
from unittest.mock import patch, MagicMock
from .model import AnthropicModel, VertexAIModel, GroqModel, ModelManager, ModelRequestException

def test_anthropic_model_generate_content():
    model = AnthropicModel('claude-3-5-sonnet-20240620')
    conversation = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Hello'}
    ]
    response = model.generate_content(conversation)
    
    # Check that a response is returned
    assert response is not None
    
    # Check that the response is a non-empty string
    assert isinstance(response, str)
    assert len(response) > 0
    
    # Check that the response doesn't contain any error messages
    assert "Error:" not in response
    
    # Optionally, you could check for some expected keywords or patterns
    # For example, if you expect a greeting in return:
    assert any(word in response.lower() for word in ['hello', 'hi', 'greetings'])

def test_vertex_ai_model_generate_content():
    model = VertexAIModel('gemini-pro')
    conversation = [
        {'role': 'system', 'parts': [{'text': 'You are a helpful assistant.'}]},
        {'role': 'user', 'parts': [{'text': 'Hello'}]}
    ]
    response = model.generate_content(conversation)
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Error:" not in response
    assert any(word in response.lower() for word in ['hello', 'hi', 'greetings'])

def test_groq_model_generate_content():
    model = GroqModel('mixtral-8x7b-32768')
    conversation = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Hello'}
    ]
    response = model.generate_content(conversation)
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Error:" not in response
    assert any(word in response.lower() for word in ['hello', 'hi', 'greetings'])

def test_model_manager():
    anthropic_model = ModelManager.initialize_model('anthropic')
    assert isinstance(anthropic_model, AnthropicModel)
    
    vertex_model = ModelManager.initialize_model('google-vertex')
    assert isinstance(vertex_model, VertexAIModel)
    
    groq_model = ModelManager.initialize_model('groq')
    assert isinstance(groq_model, GroqModel)
    
    with pytest.raises(ValueError):
        ModelManager.initialize_model('unsupported_model')

def test_model_manager_with_id():
    anthropic_model = ModelManager.initialize_model_with_id('anthropic', 'claude-3-5-sonnet-20240620')
    assert isinstance(anthropic_model, AnthropicModel)
    assert anthropic_model.model_id == 'claude-3-5-sonnet-20240620'
    
    vertex_model = ModelManager.initialize_model_with_id('google-vertex', 'gemini-pro')
    assert isinstance(vertex_model, VertexAIModel)
    assert vertex_model.model_id == 'gemini-pro'
    
    groq_model = ModelManager.initialize_model_with_id('groq', 'mixtral-8x7b-32768')
    assert isinstance(groq_model, GroqModel)
    assert groq_model.model_id == 'mixtral-8x7b-32768'