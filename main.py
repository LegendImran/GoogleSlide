
import os
import base64
import json
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# Define the required scopes for the Slides API
SCOPES = ['https://www.googleapis.com/auth/presentations']

@app.route('/add_slide', methods=['POST'])
def add_slide_and_text():
    """
    Adds a new slide with a title and body text to a presentation.
    Expects a JSON payload with 'presentation_id', 'title', and 'text'.
    Service account credentials must be passed in the 'X-Service-Account-Credentials' header
    as a base64-encoded JSON string.
    """
    # 1. Get credentials from the header
    encoded_creds = request.headers.get('X-Service-Account-Credentials')
    if not encoded_creds:
        return jsonify({'error': 'Missing X-Service-Account-Credentials header'}), 400

    try:
        # Decode the base64 string to a JSON string, then parse it
        creds_json_str = base64.b64decode(encoded_creds).decode('utf-8')
        creds_info = json.loads(creds_json_str)
        credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    except Exception as e:
        return jsonify({'error': f'Invalid or malformed credentials: {e}'}), 400

    # 2. Get data from the request body
    data = request.get_json()
    if not data or 'presentation_id' not in data or 'title' not in data or 'text' not in data:
        return jsonify({'error': 'Request body must include presentation_id, title, and text'}), 400

    presentation_id = data['presentation_id']
    slide_title = data['title']
    slide_text = data['text']
    
    try:
        # 3. Build the Google Slides API service
        service = build('slides', 'v1', credentials=credentials)

        # 4. Define elements for the new slide
        new_slide_id = "new_slide"
        title_shape_id = "title_shape"
        body_shape_id = "body_shape"
        
        # 5. Construct the API request payload
        requests = [
            {
                # Create a new slide with a standard TITLE_AND_BODY layout
                'createSlide': {
                    'objectId': new_slide_id,
                    'slideLayoutReference': {
                        'predefinedLayout': 'TITLE_AND_BODY'
                    },
                    'placeholderIdMappings': [
                        {
                            'layoutPlaceholder': { 'type': 'TITLE' },
                            'objectId': title_shape_id,
                        },
                        {
                            'layoutPlaceholder': { 'type': 'BODY' },
                            'objectId': body_shape_id,
                        }
                    ]
                }
            },
            {
                # Insert the title text into the title placeholder
                'insertText': {
                    'objectId': title_shape_id,
                    'text': slide_title,
                    'insertionIndex': 0,
                }
            },
            {
                # Insert the body text into the body placeholder
                'insertText': {
                    'objectId': body_shape_id,
                    'text': slide_text,
                    'insertionIndex': 0,
                }
            }
        ]

        # 6. Execute the batchUpdate request
        body = {'requests': requests}
        response = service.presentations().batchUpdate(presentationId=presentation_id, body=body).execute()
        
        created_slide_id = response['replies'][0]['createSlide']['objectId']
        
        return jsonify({
            'message': 'Successfully added a new slide.',
            'presentationId': presentation_id,
            'createdSlideId': created_slide_id
        }), 201

    except HttpError as err:
        return jsonify({'error': f'Google Slides API error: {err}'}), 500
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

if __name__ == '__main__':
    # Using port 8080, which is common for serverless containers
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
