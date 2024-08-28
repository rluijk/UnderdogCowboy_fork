import pytest
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