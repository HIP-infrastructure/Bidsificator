import os
import json
import shutil
from pathlib import Path

from textwrap import dedent
from urllib.parse import unquote

from flask import Flask
from flask import request
from flask import jsonify
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from flasgger import Swagger

from .core.BidsFolder import BidsFolder
from .core.BidsUtilityFunctions import BidsUtilityFunctions

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

@app.route('/datasets/<string:dataset_name>', methods=['GET'])
def get_dataset_description_and_participants(dataset_name):
    """
        Get the description and participants of a dataset
        ---
        tags:
            - BIDS
        parameters:
            - name: dataset_name
              in: path
              type: string
              required: true
              description: Name of the dataset
        responses:
            200:
                description: Success, returns the dataset description and participants
                content:
                    application/json:
                        example:
                            {
                                "Name": "Example Dataset",
                                "BIDSVersion": "1.0.0",
                                "License": "CC0",
                                "Authors": ["Author1", "Author2"],
                                "Acknowledgements": "",
                                "HowToAcknowledge": "",
                                "Funding": [""],
                                "ReferencesAndLinks": [""],
                                "DatasetDOI": "",
                                "Participants": [
                                    {
                                        "participant_id": "sub-01",
                                        "age": "25",
                                        "sex": "M",
                                        "hand": "R"
                                    }
                                ],
                                "Path": "/data/Example Dataset"
                            }
    """
    dataset_path = "/data/" + BidsUtilityFunctions.clean_string(unquote(dataset_name))
    participant_file_path = str(dataset_path) + "/participants.tsv"
    dataset_description_file_path = str(dataset_path) + "/dataset_description.json"

    #Read description of dataset and participant list
    dataset_description = BidsUtilityFunctions.read_json_safely(dataset_description_file_path)  
    participants = BidsUtilityFunctions.read_tsv_safely(participant_file_path) 
  
    #add participants list and dataset_path to returned struct
    dataset_description["Participants"] = participants
    dataset_description["Path"] = dataset_path

    response = app.response_class(
        response=json.dumps(dataset_description),
        status=200,
        mimetype='application/json'
    )
    
    return response


@app.route('/files', methods=['GET'])
def get_files_from_absolute_path():
    """
        Get the files from an absolute path
        ---
        tags:
            - Files
        parameters:
            - name: path
              in: query
              type: string
              required: true
              description: Absolute path to check
        responses:
            200:
                description: Success, returns a list of files and directories
                content:
                    application/json:
                        example:
                            [
                                {
                                    "name": "file1.txt",
                                    "isDirectory": false,
                                    "path": "/path/to/file1.txt",
                                    "parentPath": "/path/to"
                                },
                                {
                                    "name": "directory1",
                                    "isDirectory": true,
                                    "path": "/path/to/directory1",
                                    "parentPath": "/path/to"
                                }
                            ]
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

@app.route('/files/content', methods=['GET'])
def get_files_content_from_absolute_path():
    """
        Get the content of a file from an absolute path
        ---
        tags:
            - Files
        parameters:
            - name: path
              in: query
              type: string
              required: true
              description: Absolute path to the file
        responses:
            200:
                description: Success, returns the content of the file
                content:
                    application/json:
                        example:
                            "file content"
    """
    absolute_file_path_to_check = request.args.get('path')
    extensions = [".csv", ".tsv", ".txt", ".json"]
    is_text_extension = any(absolute_file_path_to_check.endswith(ext) for ext in extensions)
    if os.path.exists(absolute_file_path_to_check) and is_text_extension:
        with open(absolute_file_path_to_check, 'r') as f:
          content = f.read()
          return jsonify(content), 200
    else:
        return jsonify(""), 200

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
    dataset_path = "/data/" + BidsUtilityFunctions.clean_string(content.get('Name', ''))

    #Create a unique folder name
    dataset_path = BidsUtilityFunctions.get_unique_path(dataset_path)
    #Reset Name in content in case it was modified
    content["Name"] = os.path.basename(dataset_path).replace("_", " ")
    
    participant_file_path = str(dataset_path) + "/participants.tsv"
    dataset_description_file_path = str(dataset_path) + "/dataset_description.json"

    bids_folder = BidsFolder(dataset_path)
    bids_folder.create_folders()
    bids_folder.generate_dataset_description_file(content, dataset_description_file_path)
    bids_folder.generate_participants_tsv(participant_file_path)

    return jsonify(content), 200

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
    try:
        bids_subject = bids_folder.add_bids_subject(subject_id, subject_description)
    except ValueError as e:
        return jsonify({ 'data': 'Error: there is already a subject with this ID' }), 400
    #Generate participants.tsv
    bids_folder.generate_participants_tsv(participant_file_path)

    return jsonify({ 'data': 'Success' }), 201

@app.route('/datasets/<string:dataset_name>/participants/key', methods=['POST'])
def add_key_to_participants_list(dataset_name):
    """
        Add a new key to all participants in a dataset
        ---
        tags:
            - BIDS
        parameters:
            - name: dataset_name
              in: path
              type: string
              required: true
              description: Name of the dataset
            - name: body
              in: body
              required: true
              schema:
                type: object
                properties:
                    name:
                        type: string
                        required: true
                example:
                    name: "new_key"
        responses:
            200:
                description: Success, returns the updated participants.tsv content
                content:
                    application/json:
                        example:
                            {
                                "participant_id": "sub-01",
                                "new_key": ""
                            }
            404:
                description: Dataset not found
                content:
                    application/json:
                        example:
                            {
                                "error": "Dataset not found"
                            }
    """
    dataset_path = "/data/" + dataset_name + "/"
    participant_file_path = str(dataset_path) + "/participants.tsv"
    content = request.get_json()
    key_name = content.get('name', '')
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404
    
    bids_folder = BidsFolder(dataset_path)
    subjects = bids_folder.get_bids_subjects()
    for subject in subjects:
        subject.add_optional_key(key_name)
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

            elif file["modality"] == "T1w" or file["modality"] == "T2w" or file["modality"] == "T1rho" or file["modality"] == "T2*" or file["modality"] == "FLAIR" or file["modality"] == "CT":            
                bids_subject.add_anatomical_file(file_path, file)

            else:
                print("modality not recognized : ", file["modality"])
        else:
            print("file does not exist : ", file_path)

    return jsonify({ 'data': 'Success' }), 200

@app.route('/datasets/<string:dataset_name>', methods=['PUT'])
def update_bids_dataset(dataset_name):
    """
        Update a BIDS dataset
        ---
        tags:
            - BIDS
        parameters:
            - name: dataset_name
              in: path
              type: string
              required: true
              description: Name of the dataset
            - name: body
              in: body
              required: true
              schema:
                type: object
                properties:
                    Name:
                        type: string
                        description: New name of the dataset
                    # Add other properties here as needed
                example:
                    Name: "new_dataset_name"
        responses:
            200:
                description: Success
                content:
                    application/json:
                        example:
                            {
                                "Name": "new_dataset_name"
                            }
            404:
                description: Dataset not found
                content:
                    application/json:
                        example:
                            {
                                "error": "Dataset not found"
                            }
    """
    dataset_path = "/data/" + BidsUtilityFunctions.clean_string(unquote(dataset_name))
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404

    #Get information from request
    dataset_description = request.get_json()
    
    #We need to check if the updated name already exists
    new_dataset_path = "/data/" + BidsUtilityFunctions.clean_string(dataset_description.get('Name', ''))
    #Create a unique folder name
    new_dataset_path = BidsUtilityFunctions.get_unique_path(new_dataset_path)
    #Update Name in content in case it was modified
    dataset_description["Name"] = os.path.basename(new_dataset_path).replace("_", " ")
    
    #Then business as usual
    sanitized_dataset_name = BidsUtilityFunctions.clean_string(dataset_description.get('Name', ''))
    
    bids_folder = BidsFolder(dataset_path)
    if bids_folder.get_dataset_name() != sanitized_dataset_name:
        bids_folder.rename_dataset(sanitized_dataset_name)
    bids_folder.generate_dataset_description_file(dataset_description)
    
    return jsonify(dataset_description), 200

@app.route('/datasets/<string:dataset_name>/participants/<string:participant_name>', methods=['PUT'])
def update_bids_subject(dataset_name, participant_name):
    """
        Update a BIDS subject in a dataset
        ---
        tags:
            - BIDS
        parameters:
            - name: dataset_name
              in: path
              type: string
              required: true
              description: Name of the dataset
            - name: body
              in: body
              required: true
              schema:
                type: object
                properties:
                    participant_id:
                        type: string
                        required: true
                    age:
                        type: string
                        description: Optional key-value pair
                    sex:
                        type: string
                        description: Optional key-value pair
                    hand:
                        type: string
                        description: Optional key-value pair
                example:
                    participant_id: "sub-01"
                    age: "25"
                    sex: "M"
                    hand: "R"
        responses:
            200:
                description: Success
                content:
                    application/json:
                        example:
                            {
                                "data": "Success"
                            }
            404:
                description: Dataset or Subject not found
                content:
                    application/json:
                        example:
                            {
                                "error": "Dataset not found"
                            }
                    application/json:
                        example:
                            {
                                "error": "Subject not found"
                            }
    """
    # Check if dataset exists
    dataset_path = "/data/" + dataset_name + "/"
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404
    
    # Check if subject exists
    bids_folder = BidsFolder(dataset_path)
    subject = bids_folder.get_bids_subject(participant_name)
    if subject is None:
        return jsonify({ 'error': 'Subject not found' }), 404
    
    # Get information from request
    subject_description = request.get_json()
    subject_id = subject_description["participant_id"]
    subject_description.pop("participant_id", None)

    # Update subject ID if necessary
    if subject.get_subject_id() != subject_id:
        subject.set_subject_id(subject_id)

    # for each key value pair in subject_description
    # update the corresponding key and value in the subject
    for key, value in subject_description.items():
        subject.update_optional_key(key, value)
    bids_folder.generate_participants_tsv()
    return jsonify({ 'data': 'Success' }), 200

@app.route('/datasets/<string:dataset_name>', methods=['DELETE'])
def delete_bids_dataset(dataset_name):
    """
    Delete a BIDS dataset
    ---
    tags:
        - BIDS
    description: A success message indicating that the dataset was deleted.
    parameters:
    - name: dataset_name
      in: query
      type: string
      required: true
      description: The name of the dataset to delete
    responses:
        200:
            description: A successful response
            examples:
                application/json: ""
    """
    dataset_path = "/data/" + BidsUtilityFunctions.clean_string(unquote(dataset_name))
    if os.path.exists(dataset_path):
        shutil.rmtree(dataset_path)
        return jsonify({ 'data': 'Success' }), 200
    else:
        return jsonify({ 'error': 'Dataset not found' }), 404

@app.route('/datasets/<string:dataset_name>/participants/<string:subject_name>', methods=['DELETE'])
def delete_bids_subject(dataset_name, subject_name):
    """
        Delete a BIDS subject from a dataset
        ---
        tags:
            - BIDS
        parameters:
            - name: dataset_name
              in: path
              type: string
              required: true
              description: Name of the dataset
            - name: subject_name
              in: path
              type: string
              required: true
              description: Name of the subject
        responses:
            200:
                description: Success
                content:
                    application/json:
                        example:
                            {
                                "data": "Success"
                            }
            404:
                description: Dataset or Subject not found
                content:
                    application/json:
                        example:
                            {
                                "error": "Dataset not found"
                            }
                    application/json:
                        example:
                            {
                                "error": "Subject not found"
                            }
    """
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

@app.route('/datasets/<string:dataset_name>/participants/key/<string:key_name>', methods=['DELETE'])
def remove_key_from_participants_list(dataset_name, key_name):
    """
        Delete a key from all participants in a dataset
        ---
        tags:
            - BIDS
        parameters:
            - name: dataset_name
              in: path
              type: string
              required: true
              description: Name of the dataset
            - name: key_name
              in: path
              type: string
              required: true
              description: Name of the key to delete
        responses:
            200:
                description: Success, returns the updated participants.tsv content
                content:
                    application/json:
                        example:
                            {
                                "participant_id": "sub-01"
                            }
            404:
                description: Dataset not found
                content:
                    application/json:
                        example:
                            {
                                "error": "Dataset not found"
                            }
    """
    dataset_path = "/data/" + dataset_name + "/"
    participant_file_path = str(dataset_path) + "/participants.tsv"
    if not os.path.exists(dataset_path):
        return jsonify({ 'error': 'Dataset not found' }), 404

    bids_folder = BidsFolder(dataset_path)
    subjects = bids_folder.get_bids_subjects()
    for subject in subjects:
        subject.remove_optional_key(key_name)
    bids_folder.generate_participants_tsv()

    return jsonify(BidsUtilityFunctions.read_tsv_safely(participant_file_path)), 200

def main():
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    main()
