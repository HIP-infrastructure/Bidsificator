import csv
import os
import json

class BidsUtilityFunctions:
    @staticmethod
    def read_tsv_safely(filename: str) -> list:
        """
        This function reads a TSV file and returns the content as a list of dictionaries.
        If the file does not exist, an empty list is returned.

        Parameters:
        filename (str): The path to the TSV file

        Returns:
        list: The content of the TSV file as a list of dictionaries
        """
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
    def read_json_safely(filename: str) -> str:
        """
        This function reads a JSON file and returns the content as a string.
        If the file does not exist, an empty string is returned.

        Parameters:
        filename (str): The path to the JSON file

        Returns:
        str: The content of the JSON file
        """
        json_raw_content = ""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                json_raw_content = json.load(f)
        return json_raw_content
    
    @staticmethod
    def get_unique_path(path):
        """
        This function takes a path as input and returns a unique path.
        If the input path does not exist, it is returned as is.
        If the input path exists, a unique path is generated by appending a number to the path.
        The number is incremented until a unique path is found.

        Parameters:
        path (str): The input path
        
        Returns:
        str: The unique path
        """
        if not os.path.exists(path):
            return path

        i = 1
        while os.path.exists(f"{path}({i})"):
            i += 1

        return f"{path}({i})"
    
    @staticmethod
    def clean_string(input_string):
        """
        This function takes a string as input and returns a cleaned version of the string.
        The cleaning process involves:
        1. Removing leading and trailing white spaces
        2. Replacing middle white spaces with underscores

        Parameters:
        input_string (str): The string to be cleaned

        Returns:
        str: The cleaned string
        """
        cleaned_string = input_string.strip()
        cleaned_string = cleaned_string.replace(" ", "_")  
        return cleaned_string