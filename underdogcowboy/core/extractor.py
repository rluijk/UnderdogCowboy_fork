import json
from typing import Any, Dict, List, Tuple, Union

class JSONExtractor:
    def __init__(self, text: str, expected_keys: List[str]) -> None:
        self.text = text
        self.expected_keys = expected_keys

    def extract_and_parse_json(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        try:
            json_str = self.extract_json_str()
            parsed_json = json.loads(json_str)
            inspection_data = self.inspect_parsed_json(parsed_json)
            return parsed_json, inspection_data
        except (ValueError, KeyError) as e:
            return {}, {"error": str(e)}

    def extract_json_str(self) -> str:
        start_index = self.text.find("{")
        end_index = self.text.rfind("}") + 1
        return self.text[start_index:end_index]

    def inspect_parsed_json(self, parsed_json: Dict[str, Any]) -> Dict[str, Any]:
        inspection_data: Dict[str, Any] = {}
        for key in self.expected_keys:
            if key not in parsed_json:
                inspection_data[f"missing_{key}"] = True
            else:
                inspection_data[f"has_{key}"] = True
        return inspection_data