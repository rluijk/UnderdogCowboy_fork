import json

class JSONExtractor:
    def __init__(self, text, expected_keys=None):
        self.text = text
        self.expected_keys = expected_keys
        self.json_data = None
        self.inspection_data = None

    def extract_and_parse_json(self):
        brace_count = 0
        json_start = -1
        json_end = -1

        for i, char in enumerate(self.text):
            if char == '{':
                if brace_count == 0:
                    json_start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_start != -1 and json_end != -1:
            json_str = self.text[json_start:json_end]
            try:
                self.json_data = json.loads(json_str)
                self.inspection_data = self.generate_inspection_data()
                return self.json_data, self.inspection_data
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                return None, None
        else:
            print("No JSON object found in the text")
            return None, None

    def generate_inspection_data(self):
        inspection_data = {}
        keys = list(self.json_data.keys())
        values_presence = {key: self.json_data[key] is not None for key in keys}

        inspection_data['number_of_keys'] = len(keys)
        inspection_data['keys'] = keys
        inspection_data['values_presence'] = values_presence

        if self.expected_keys:
            inspection_data['keys_match'] = set(keys) == set(self.expected_keys)

        return inspection_data # new diff 1 augustus

    def check_inspection_data(self, expected_data): #diff second round test ok and 3th like below
        deviations = {}
        is_correct = True # diff test change with some extras

        # Compare number of keys
        if self.inspection_data['number_of_keys'] != expected_data['number_of_keys']:
            deviations['number_of_keys'] = self.inspection_data['number_of_keys']
            is_correct = False

        # Compare keys list
        if set(self.inspection_data['keys']) != set(expected_data['keys']):
            deviations['keys'] = self.inspection_data['keys']
            is_correct = False

        # Compare values presence
        values_presence_deviation = {
            key: self.inspection_data['values_presence'][key] != expected_data['values_presence'][key]
            for key in expected_data['values_presence']
            if self.inspection_data['values_presence'][key] != expected_data['values_presence'][key]
        }

        if values_presence_deviation:
            deviations['values_presence'] = values_presence_deviation
            is_correct = False

        # Compare keys match
        if 'keys_match' in self.inspection_data and self.inspection_data['keys_match'] != expected_data['keys_match']:
            deviations['keys_match'] = self.inspection_data['keys_match']
            is_correct = False

        return is_correct, deviations