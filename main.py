from flask import Flask, request, jsonify, render_template
import openai
import time
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Constants
ASSISTANT_ID = "asst_SizeRJtLIRnks53yEh8G6fU5"
MAX_RETRIES = 10
INITIAL_RETRY_DELAY = 1
MAX_RETRY_DELAY = 5

# Initialize OpenAI client
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    client = openai.Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing OpenAI client: {str(e)}")
    client = None

def wait_for_run_completion(thread_id, run_id, max_retries=MAX_RETRIES):
    """Wait for the assistant's run to complete with retry logic."""
    retry_count = 0
    delay = INITIAL_RETRY_DELAY

    while retry_count < max_retries:
        try:
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            
            if run.status == "completed":
                return run
            elif run.status in ["failed", "expired", "cancelled"]:
                raise Exception(f"Run ended with status: {run.status}")
            
            # Exponential backoff with max delay
            delay = min(delay * 1.5, MAX_RETRY_DELAY)
            time.sleep(delay)
            retry_count += 1
            
        except Exception as e:
            print(f"Error checking run status: {str(e)}")
            raise

    raise Exception("Maximum retries reached while waiting for run completion")

@app.route('/chat', methods=['POST'])
def chat():
    # Verify OpenAI client is initialized
    if not client:
        return jsonify({'response': 'OpenAI client not properly initialized'}), 500

    # Validate request
    if not request.is_json:
        return jsonify({'response': 'Request must be JSON'}), 400
    
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'response': 'No message provided'}), 400

    try:
        # Create thread and run
        thread = client.beta.threads.create(messages=[{"role": "user", "content": user_message}])
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)

        # Wait for completion
        run = wait_for_run_completion(thread.id, run.id)

        # Get response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if not messages.data:
            return jsonify({'response': 'No response received from assistant'}), 500

        # Process and return response
        response = messages.data[0].content[0].text.value
        cleaned_response = re.sub(r'【[^】]+】', '', response)
        return jsonify({'response': cleaned_response})

    except Exception as e:
        error_msg = str(e)
        print(f"Error in chat endpoint: {error_msg}")
        return jsonify({
            'response': 'An error occurred while processing your request',
            'error': error_msg
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

# For local development only
