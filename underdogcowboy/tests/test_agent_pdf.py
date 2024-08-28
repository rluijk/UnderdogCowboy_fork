import pytest
from unittest.mock import patch, MagicMock, Mock 

# Import the main function and other necessary components
from underdogcowboy.core.commandtools.agent_pdf import main, DialogueProcessor, LLMConfigManager

@pytest.fixture
def mock_config_manager():
    config_manager = Mock(spec=LLMConfigManager)
    config_manager.get_general_config.return_value = {
        'dialog_save_path': '/tmp/dialogs',
        'some_other_config': 'value'
    }
    return config_manager

@pytest.fixture
def dialogue_processor(mock_config_manager):
    return DialogueProcessor(mock_config_manager)


@patch('os.path.expanduser')
def test_dialogue_processor_initialization(mock_expanduser, mock_config_manager):
    """
    Test the initialization of DialogueProcessor.
    
    This test verifies that:
    1. The config_manager is correctly set during initialization.
    2. The agents_dir is correctly set and expanded.
    3. os.path.expanduser is called with the correct default path.

    Args:
        mock_expanduser (MagicMock): Mocked version of os.path.expanduser.
        mock_config_manager (Mock): Mocked LLMConfigManager.
    """
    mock_expanduser.return_value = '/home/user/.underdogcowboy/agents'
    
    dialogue_processor = DialogueProcessor(mock_config_manager)
    
    assert dialogue_processor.config_manager == mock_config_manager
    assert dialogue_processor.agents_dir == '/home/user/.underdogcowboy/agents'
    mock_expanduser.assert_called_once_with('~/.underdogcowboy/agents')


def test_get_dialog_save_path(dialogue_processor, mock_config_manager):
    save_path = dialogue_processor.config_manager.get_general_config()['dialog_save_path']
    assert save_path == '/tmp/dialogs'
    mock_config_manager.get_general_config.assert_called_once()

def test_export_pdf_uses_config_path(dialogue_processor, mock_config_manager, tmp_path):
    # Setup
    dialogue_processor.agent_data = {'history': []}
    dialogue_processor.current_agent_file = 'test_agent.json'
    mock_config_manager.get_general_config.return_value = {'dialog_save_path': str(tmp_path)}
    
    # Mock PDFGenerator
    mock_pdf_generator = Mock()
    dialogue_processor.pdf_generator = mock_pdf_generator
    
    # Call the method
    dialogue_processor.do_export_pdf('test_output.pdf')
    
    # Assert
    expected_path = tmp_path / 'test_output.pdf'
    mock_pdf_generator.generate_pdf.assert_called_once_with(
        str(expected_path),
        "Dialogue Export",
        [],
        'test_agent.json'
    )


def test_main():
    # Mock LLMConfigManager
    mock_config_manager = MagicMock(spec=LLMConfigManager)
    
    # Mock DialogueProcessor
    mock_dialogue_processor = MagicMock(spec=DialogueProcessor)
    
    # Patch the LLMConfigManager and DialogueProcessor
    with patch('underdogcowboy.core.commandtools.agent_pdf.LLMConfigManager', return_value=mock_config_manager) as mock_config_manager_class:
        with patch('underdogcowboy.core.commandtools.agent_pdf.DialogueProcessor', return_value=mock_dialogue_processor) as mock_dialogue_processor_class:
            # Call the main function
            main()
            
            # Assert that LLMConfigManager was instantiated
            mock_config_manager_class.assert_called_once()
            
            # Assert that DialogueProcessor was instantiated with the config manager
            mock_dialogue_processor_class.assert_called_once_with(mock_config_manager)
            
            # Assert that cmdloop was called on the DialogueProcessor instance
            mock_dialogue_processor.cmdloop.assert_called_once()
