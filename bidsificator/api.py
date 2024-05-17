import os
import csv
import json
import pathlib
from pathlib import Path
from flask import Flask
from flask import request
from flask import jsonify
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from core.BidsFolder import BidsFolder
from core.BidsUtilityFunctions import BidsUtilityFunctions
from flasgger import Swagger
from textwrap import dedent


__author__ = "Florian SIPP"
__email__ = "florian.sipp@chuv.ch"

app = Flask(__name__)
swagger = Swagger(app, template={
    "info": {
        "title": "BIDS Toolbox API",
        "description": "An API to interact with BIDS datasets.",
        "version": "1.0.0"
    }
})

CORS(app) 
auth = HTTPBasicAuth()

#TODO add_files_to_bids_subject(dataset_name): Check with manu how to handle error return if some files are missing but not all 
#TODO Add name sanitization to handle possible spaces in dataset name

@app.route('/')
def index():
  return dedent("""
        <!doctype HTML>
        <meta charset=utf-8>
        <title>BIDS Toolbox API</title>
        <ul>
            <li><a href="/apidocs">Swagger UI</a>
        </ul>
        """)

@app.route('/ok')
#@auth.login_required
def health_check():
  return "Bids Backend currently running on localhost"

@app.route('/datasets', methods=['GET'])
def get_all_datasets():
    """
        Retrieve all datasets
        ---
        tags:
            - BIDS
        description: Returns a list of datasets.
        responses:
            200:
                description: A successful response
                examples:
                    application/json:
                        [
                            {
                                "Name": "Example Dataset",
                                "BIDSVersion": "1.0.2",
                                "License": "CC0",
                                "Authors": ["John Doe", "Jane Doe"],
                                "Acknowledgements": "",
                                "HowToAcknowledge": "",
                                "Funding": ["Grant 1234"],
                                "ReferencesAndLinks": ["https://example.com"],
                                "DatasetDOI": "10.0.2.3/abcd1234"
                            }
                        ]
        """
    datasets = []
    for dataset in os.listdir('/data'):
        dataset_description_file_path = "/data/" + dataset + "/dataset_description.json"
        if os.path.exists(dataset_description_file_path):
            with open(dataset_description_file_path, 'r') as f:
                dataset_description = json.load(f)
                datasets.append(dataset_description)

    return jsonify(datasets), 200

@app.route('/datasets', methods=['POST'])
def create_bids_dataset():
    """
    Create a new BIDS dataset
    ---
    tags:
        - BIDS
    description: Returns the description of the created dataset.
    parameters:
    - name: dataset_dirname
      in: query
      type: string
      required: true
      description: The directory name of the new dataset
    - name: DatasetDescJSON
      in: query
      type: object
      required: true
      description: The description of the new dataset
      schema:
        type: object
        properties:
          Name:
            type: string
            description: The name of the dataset
          BIDSVersion:
            type: string
            description: The BIDS version of the dataset
          License:
            type: string
            description: The license of the dataset
          Authors:
            type: array
            items:
              type: string
            description: The authors of the dataset
          Acknowledgements:
            type: string
            description: The acknowledgements for the dataset
          HowToAcknowledge:
            type: string
            description: How to acknowledge the dataset
          Funding:
            type: array
            items:
              type: string
            description: The funding sources for the dataset
          ReferencesAndLinks:
            type: array
            items:
              type: string
            description: The references and links for the dataset
          DatasetDOI:
            type: string
            description: The DOI of the dataset
    responses:
        200:
            description: A successful response
            examples:
                application/json: 
                    {
                        "Name": "Example Dataset",
                        "BIDSVersion": "1.0.2",
                        "License": "CC0",
                        "Authors": ["John Doe", "Jane Doe"],
                        "Acknowledgements": "",
                        "HowToAcknowledge": "",
                        "Funding": ["Grant 1234"],
                        "ReferencesAndLinks": ["https://example.com"],
                        "DatasetDOI": "10.0.2.3/abcd1234"
                    }
    """
    # Retrieve user information from the JSON request
    content = request.get_json()
    dataset_path = "/data/" + content.get('dataset_dirname', '')
    dataset_description = content.get('DatasetDescJSON', '')

    participant_file_path = str(dataset_path) + "/participants.tsv"
    dataset_description_file_path = str(dataset_path) + "/dataset_description.json"

    bids_folder = BidsFolder(dataset_path)
    bids_folder.create_folders()
    bids_folder.generate_dataset_description_file(dataset_description, dataset_description_file_path)
    bids_folder.generate_participants_tsv(participant_file_path)

    return jsonify(dataset_description), 200

@app.route('/datasets/<string:dataset_name>/participants', methods=['POST'])
def create_empty_bids_subject(dataset_name):
    """
        Create a new BIDS subject within a specified dataset.
        ---
        tags:
            - BIDS
        description: A success message indicating that the subject was created.
        parameters:
        - name: dataset_name
          in: query
          type: string
          required: true
          description: The name of the dataset
        - name: subjects
          in: query
          type: object
          required: true
          description: A list of subjects to create, each represented as a dictionary with a 'sub' key indicating the subject ID, and a list of key-value pairs for additional subject information.
          schema:
            type: object
            properties:
            participant_id:
                type: string
                description: The ID of the participant
        responses:
            200:
                description: A successful response
                examples:
                    application/json: ""
    """
    #Get information from request
    dataset_path = "/data/" + dataset_name + "/"
    subject_description = request.get_json()
    #Create useful paths
    participant_file_path = str(dataset_path) + "/participants.tsv"
    dataset_description_file_path = str(dataset_path) + "/dataset_description.json"
    #Create folders
    bids_folder = BidsFolder(dataset_path)
    bids_folder.create_folders()
    bids_folder.generate_empty_dataset_description_file(dataset_name, dataset_description_file_path)

    #Create subject
    subject_id = subject_description["participant_id"]
    subject_description.pop("participant_id", None)
    bids_subject = bids_folder.add_bids_subject(subject_id, subject_description)
    #Generate participants.tsv
    bids_folder.generate_participants_tsv(participant_file_path)

    return jsonify({ 'data': 'Success' }), 201

# in the body 
# {
#   "participant_id": "01",
#   "optionnal_key": "25",
#   "optionnal_key2": "M",
#   "optionnal_key3": "CHUV"
# }
@app.route('/datasets/<string:dataset_name>/participants', methods=['PUT'])
def update_bids_subject(dataset_name):
    dataset_path = "/data/" + dataset_name + "/"
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404
    
    #Get information from request
    subject_description = request.get_json()
    subject_id = subject_description["participant_id"]
    subject_description.pop("participant_id", None)

    bids_folder = BidsFolder(dataset_path)
    subject = bids_folder.get_bids_subject(subject_id)
    if subject is None:
        return jsonify({ 'error': 'Subject not found' }), 404
    
    #for each key value pair in subject_description
    #update the corresponding key and value in the subject
    for key, value in subject_description.items():
        subject.update_optional_key(key, value)
    bids_folder.generate_participants_tsv()
    return jsonify({ 'data': 'Success' }), 200

@app.route('/datasets/<string:dataset_name>/participants/<string:subject_name>', methods=['DELETE'])
def delete_bids_subect(dataset_name, subject_name):
    dataset_path = "/data/" + dataset_name + "/"
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404

    bids_folder = BidsFolder(dataset_path)
    subjects = bids_folder.get_bids_subject(subject_name)
    if subjects is None:
        return jsonify({ 'error': 'Subject not found' }), 404
    
    bids_folder.delete_bids_subject(subject_name)
    bids_folder.generate_participants_tsv()
    return jsonify({ 'data': 'Success' }), 200

@app.route('/datasets/<string:dataset_name>/participants/key', methods=['POST'])
def add_key_to_participants_list(dataset_name):    
    dataset_path = "/data/" + dataset_name + "/"
    participant_file_path = str(dataset_path) + "/participants.tsv"
    content = request.get_json()
    key_name = content.get('name', '')
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404
    
    bids_folder = BidsFolder(dataset_path)
    subjects = bids_folder.get_bids_subects()
    for subject in subjects:
        subject.add_optional_key(key_name)
    bids_folder.generate_participants_tsv()

    return jsonify(BidsUtilityFunctions.read_tsv_safely(participant_file_path)), 200

@app.route('/datasets/<string:dataset_name>/participants/key/<string:key_name>', methods=['DELETE'])
def remove_key_from_participants_list(dataset_name, key_name):
    dataset_path = "/data/" + dataset_name + "/"
    participant_file_path = str(dataset_path) + "/participants.tsv"
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404

    bids_folder = BidsFolder(dataset_path)
    subjects = bids_folder.get_bids_subects()
    for subject in subjects:
        subject.remove_optional_key(key_name)
    bids_folder.generate_participants_tsv()

    return jsonify(BidsUtilityFunctions.read_tsv_safely(participant_file_path)), 200

@app.route('/datasets/<string:dataset_name>/files', methods=['POST'])
def add_files_to_bids_subject(dataset_name):
    """
    Add files to a BIDS subject within a specified dataset.
    ---
    tags: 
        - BIDS
    description: Return a success message indicating that the files were added.
    parameters:
        - name: files
          in: body
          required: true
          description: An array of file objects to be added to the BIDS subject
          schema:
            type: array
            items:
                type: object
                properties:
                    path:
                        type: string
                        description: The path to the file
                    modality:
                        type: string
                        description: The modality of the file
    responses:
        200:
            description: A successful response
            examples:
                application/json: ""
    """
    dataset_path = "/data/" + dataset_name + "/"
    files_description = request.get_json()

    bids_folder = BidsFolder(dataset_path)
    for file in files_description:
        bids_subject = bids_folder.get_bids_subject(file["subject"])
        if bids_subject is None:
            return jsonify({ 'error': 'Subject not found' }), 404

        file_path = Path(file["path"])
        if file_path.exists():
            if file["modality"] == "ieeg":
                new_file_path = bids_subject.add_functionnal_file(file_path, file["entities"])
                bids_subject.generate_events_file(new_file_path, file["entities"])
                bids_subject.generate_channels_file(new_file_path, file["entities"])
                bids_subject.generate_task_file(new_file_path, file["entities"])

            elif file["modality"] == "T1w" or file["modality"] == "T2w" or file["modality"] == "T1rho" or file["modality"] == "T2rho" or file["modality"] == "FLAIR":            
                bids_subject.add_anatomical_file(file_path, file)

            else:
                print("modality not recognized : ", file["modality"])
        else:
            print("file does not exist : ", file_path)

    return jsonify({ 'data': 'Success' }), 200

""" Retrieve the description and participants of a specified dataset.
Endpoint: GET /datasets/string:dataset_name

Parameters:
    - dataset_name (str): The name of the dataset to retrieve information from.

Returns:
    - dict: A dictionary containing the dataset description and a list of participants.
    - tuple (str, int): An error message and HTTP status code (404 for not found) if the dataset is not found.

Description: This endpoint allows users to retrieve the description and participants of a specified dataset.
    - The 'dataset_name' parameter in the URL specifies the dataset to retrieve information from.
    - The function constructs the paths to the dataset, the participants.tsv file, and the dataset_description.json file.
    - It then checks if the dataset_description.json file exists and reads its content if it does.
    - It also checks if the participants.tsv file exists and reads its content if it does. For each line in the file (excluding the header), it extracts the subject ID and adds it to a list of participants.
    - Finally, it returns a dictionary containing the dataset description and the list of participants.

Example Usage:
```http
GET /datasets/my_dataset
"""
@app.route('/datasets/<string:dataset_name>', methods=['GET'])
def get_dataset_description_and_participants(dataset_name):
    """
    Retrieve the description and participants of a specified dataset.
    ---
    tags:
        - BIDS
    description: Returns the description and participants of a specified dataset.
    
    """
    dataset_path = "/data/" + dataset_name
    participant_file_path = str(dataset_path) + "/participants.tsv"
    dataset_description_file_path = str(dataset_path) + "/dataset_description.json"

    #Read description of dataset and participant list
    dataset_description = BidsUtilityFunctions.read_json_safely(dataset_description_file_path)  
    participants = BidsUtilityFunctions.read_tsv_safely(participant_file_path) 
  
    #add participants list and dataset_path to returned struct
    dataset_description["Participants"] = participants
    dataset_description["Path"] = dataset_path

    return jsonify( dataset_description ), 200

""" Retrieve the files from a specified absolute path.
Endpoint: GET /files

Parameters:
    - path (str): The absolute path to retrieve files from. This is passed as a query parameter.

Returns:
    - list: A list of dictionaries, each representing a file or directory. Each dictionary contains the name, whether it is a directory, the path, and the parent path.
    - tuple (str, int): An empty list and HTTP status code (200 for success) if the path does not exist.

Description: This endpoint allows users to retrieve the files from a specified absolute path.
    - The 'path' query parameter specifies the absolute path to retrieve files from.
    - The function checks if the path exists. If it does, it lists all files in the directory.
    - For each file, it constructs the file path, checks if it is a directory, and adds a dictionary containing the file information to a list.
    - Finally, it returns the list of files. If the path does not exist, it returns an empty list.

Example Usage:
```http
GET /files?path=/path/to/directory
"""
@app.route('/files', methods=['GET'])
def get_files_from_absolute_path():
    """
    Retrieve the files from a specified absolute path.
    """
    absolute_path_to_check = request.args.get('path')
    if os.path.exists(absolute_path_to_check):
        files = []
        for file in os.listdir(absolute_path_to_check):
            file_path = os.path.join(absolute_path_to_check, file)
            is_directory = os.path.isdir(file_path)
            files.append({
              "name": file,
              "isDirectory": is_directory,
              "path": file_path,
              "parentPath": absolute_path_to_check
            })
        return jsonify(files), 200
    else:
        return jsonify([]), 200

""" Retrieve the content of a file from a specified absolute path.
Endpoint: GET /files/content

Parameters:
    - path (str): The absolute path to the file to retrieve content from. This is passed as a query parameter.

Returns:
    - str: The content of the file.
    - tuple (str, int): An empty string and HTTP status code (200 for success) if the file does not exist or does not have a text extension (.csv, .txt, .json).

Description: This endpoint allows users to retrieve the content of a file from a specified absolute path.
    - The 'path' query parameter specifies the absolute path to the file to retrieve content from.
    - The function checks if the file exists and has a text extension. If it does, it opens the file and reads its content.
    - Finally, it returns the content of the file. If the file does not exist or does not have a text extension, it returns an empty string.

Example Usage:
```http
GET /files/content?path=/path/to/file.txt
"""
@app.route('/files/content', methods=['GET'])
def get_files_content_from_absolute_path():
    absolute_file_path_to_check = request.args.get('path')
    extensions = [".csv", ".tsv", ".txt", ".json"]
    is_text_extension = any(absolute_file_path_to_check.endswith(ext) for ext in extensions)
    if os.path.exists(absolute_file_path_to_check) and is_text_extension:
        with open(absolute_file_path_to_check, 'r') as f:
          content = f.read()
          return jsonify(content), 200
    else:
        return jsonify(""), 200

if __name__ == '__main__':
  app.run(debug=True, port=5000)