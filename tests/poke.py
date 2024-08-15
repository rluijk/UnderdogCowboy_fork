import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from underdogcowboy.core.config_manager import LLMConfigManager
from underdogcowboy.core.commandtools.poke import LLMPokeProcessor  

class TestLLMPokeProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = LLMPokeProcessor()
        self.processor.config_manager = MagicMock(spec=LLMConfigManager)
        self.processor.config_manager.get_available_models.return_value = ['model1', 'model2', 'model3']
        self.processor.available_models = self.processor.config_manager.get_available_models()

    def test_initialization(self):
        self.assertIsInstance(self.processor, LLMPokeProcessor)
        self.assertIsNotNone(self.processor.config_manager)
        self.assertIsNone(self.processor.current_model)
        self.assertEqual(self.processor.available_models, ['model1', 'model2', 'model3'])

    @patch('sys.stdout', new_callable=StringIO)
    def test_list_models(self, mock_stdout):
        self.processor.do_list_models('')
        output = mock_stdout.getvalue()
        self.assertIn('1. model1', output)
        self.assertIn('2. model2', output)
        self.assertIn('3. model3', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_select_model_by_number(self, mock_stdout):
        self.processor.do_select_model('2')
        self.assertEqual(self.processor.current_model, 'model2')
        self.assertIn('Selected model: model2', mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_select_model_by_name(self, mock_stdout):
        self.processor.do_select_model('model3')
        self.assertEqual(self.processor.current_model, 'model3')
        self.assertIn('Selected model: model3', mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_select_invalid_model(self, mock_stdout):
        self.processor.do_select_model('invalid_model')
        self.assertIsNone(self.processor.current_model)
        self.assertIn("Model 'invalid_model' not found", mock_stdout.getvalue())

    @patch('underdogcowboy.core.dialog_manager.AgentDialogManager')
    @patch('underdogcowboy.test_agent')
    @patch('sys.stdout', new_callable=StringIO)
    def test_poke(self, mock_stdout, mock_test_agent, mock_adm):
        self.processor.current_model = 'model1'
        mock_adm.return_value.model_name = 'model1'
        mock_test_agent.__rshift__.return_value = "Test response"

        self.processor.do_poke('')

        mock_adm.assert_called_once_with([mock_test_agent], model_name='model1')
        mock_test_agent.__rshift__.assert_called_once_with("small message back please, we testing if we can reach you")
        self.assertIn("Response from model1: Test response", mock_stdout.getvalue())
    
    @patch('underdogcowboy.core.dialog_manager.AgentDialogManager')
    @patch('underdogcowboy.test_agent')
    @patch('sys.stdout', new_callable=StringIO)
    def test_poke_all(self, mock_stdout, mock_test_agent, mock_adm):
        mock_adm.return_value.model_name = 'test_model'
        mock_test_agent.__rshift__.return_value = "Test response"

        self.processor.do_poke_all('')

        self.assertEqual(mock_adm.call_count, 3)
        self.assertEqual(mock_test_agent.__rshift__.call_count, 3)
        for model in self.processor.available_models:
            self.assertIn(f"Response from {model}: Test response", mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_help(self, mock_stdout):
        self.processor.do_help('')
        output = mock_stdout.getvalue()
        self.assertIn('list_models:', output)
        self.assertIn('select_model:', output)
        self.assertIn('poke:', output)
        self.assertIn('poke_all:', output)
        self.assertIn('exit:', output)

    def test_exit(self):
        result = self.processor.do_exit('')
        self.assertTrue(result)

    @patch('sys.stdout', new_callable=StringIO)
    def test_default_valid_number(self, mock_stdout):
        self.processor.default('2')
        self.assertEqual(self.processor.current_model, 'model2')
        self.assertIn('Selected model: model2', mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_default_invalid_input(self, mock_stdout):
        self.processor.default('invalid_command')
        self.assertIn('*** Unknown syntax: invalid_command', mock_stdout.getvalue())

if __name__ == '__main__':
    unittest.main()