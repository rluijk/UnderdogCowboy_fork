import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from underdogcowboy.core.commandtools.tracing_config import TracingConfigProcessor
from underdogcowboy.core.config_manager import LLMConfigManager

class TestTracingConfigProcessor(unittest.TestCase):

    def setUp(self):        
        self.processor = TracingConfigProcessor()
        self.processor.config_manager = MagicMock(spec=LLMConfigManager)

    def test_initialization(self):
        self.assertIsInstance(self.processor, TracingConfigProcessor)
        self.assertIsNotNone(self.processor.config_manager)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_command(self, mock_stdout):
        mock_config = {'use_langsmith': 'yes', 'langsmith_api_key': 'test_key'}
        self.processor.config_manager.get_tracing_config.return_value = mock_config
        
        self.processor.do_show('')
        
        output = mock_stdout.getvalue()
        self.assertIn('use_langsmith: yes', output)
        self.assertIn('langsmith_api_key: ****', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_update_command(self, mock_stdout):
        self.processor.do_update('')
        
        self.processor.config_manager.update_tracing_config.assert_called_once()
        self.assertIn('Tracing configuration updated.', mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_toggle_langsmith_command(self, mock_stdout):
        mock_config = {'use_langsmith': 'no'}
        self.processor.config_manager.get_tracing_config.return_value = mock_config
        
        self.processor.do_toggle_langsmith('')
        
        self.processor.config_manager.update_model_property.assert_called_with('tracing', 'use_langsmith', 'yes')
        self.assertIn('LangSmith tracing enabled', mock_stdout.getvalue())

    def test_exit_command(self):
        result = self.processor.do_exit('')
        self.assertTrue(result)

    @patch('sys.stdout', new_callable=StringIO)
    def test_help_command(self, mock_stdout):
        self.processor.do_help('')
        
        output = mock_stdout.getvalue()
        self.assertIn('show:', output)
        self.assertIn('update:', output)
        self.assertIn('toggle_langsmith:', output)
        self.assertIn('exit:', output)

if __name__ == '__main__':
    unittest.main()