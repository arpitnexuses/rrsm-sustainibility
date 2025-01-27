from flask import Flask, request, jsonify, render_template
import openai
import time
import os
import re
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
ASSISTANT_ID = "asst_SizeRJtLIRnks53yEh8G6fU5"
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

# Define the regex pattern for removing the source annotations
SOURCE_TAG_PATTERN = r'【[^】]+】'

def wait_for_run_completion(thread_id, run_id, timeout=60):
    """Wait for the assistant's run to complete with exponential backoff."""
    start_time = time.time()
    wait_time = 1  # Initial wait time in seconds
    
    while time.time() - start_time < timeout:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        
        if run.status == "completed":
            return run
        elif run.status == "failed":
            raise Exception(f"Run failed with reason: {run.last_error}")
        elif run.status == "expired":
            raise Exception("Run expired")
        
        # Sleep with exponential backoff
        time.sleep(min(wait_time, 10))  # Cap maximum wait at 10 seconds
        wait_time *= 1.5  # Increase wait time by 50% each iteration
    
    raise Exception(f"Run did not complete within {timeout} seconds")

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'response': 'No message provided'}), 400

    try:
        # Create a thread with the user's message
        thread = client.beta.threads.create(messages=[{
            "role": "user",
            "content": user_message,
        }])

        # Submit the thread to the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Wait for run to complete with improved handling
        run = wait_for_run_completion(thread.id, run.id)

        # Get the latest message from the thread
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        
        if not messages.data:
            return jsonify({'response': 'No response received from assistant'}), 500

        latest_message = messages.data[0].content[0].text.value

        # Clean the response message by removing source tags
        cleaned_message = re.sub(SOURCE_TAG_PATTERN, '', latest_message)

        return jsonify({'response': cleaned_message})

    except Exception as e:
        print(f"Error during chat processing: {str(e)}")
        error_message = str(e) if not isinstance(e, openai.OpenAIError) else "An error occurred with the AI service"
        return jsonify({'response': f'Error: {error_message}'}), 500


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)

