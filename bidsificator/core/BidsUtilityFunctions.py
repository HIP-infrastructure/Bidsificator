import csv
import os
import json

class BidsUtilityFunctions:
    @staticmethod
    def read_tsv_safely(filename):
        data = []
        if os.path.exists(filename):
            with open(filename, 'r', newline='') as file:
                reader = csv.reader(file, delimiter='\t')
                headers = next(reader)  # Read the header row
                for row in reader:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[headers[i]] = value
                    data.append(row_dict)
        return data
    
    @staticmethod
    def read_json_safely(filename):
        json_raw_content = ""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                json_raw_content = json.load(f)
        return json_raw_content