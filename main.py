from flask import Flask, request, jsonify, render_template
import openai
import time
import os
import re
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
ASSISTANT_ID = "asst_SizeRJtLIRnks53yEh8G6fU5"
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the regex pattern for removing the source annotations
SOURCE_TAG_PATTERN = r'【[^】]+】'


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    try:
        # Create a thread with the user's message
        thread = client.beta.threads.create(messages=[{
            "role": "user",
            "content": user_message,
        }])

        # Submit the thread to the assistant
        run = client.beta.threads.runs.create(thread_id=thread.id,
                                              assistant_id=ASSISTANT_ID)

        # Wait for run to complete
        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(thread_id=thread.id,
                                                    run_id=run.id)
            time.sleep(1)

        # Get the latest message from the thread
        message_response = client.beta.threads.messages.list(
            thread_id=thread.id)
        messages = message_response.data

        # Debug: Print the full message response structure
        print("Full message response:", messages)

        latest_message = messages[0].content[0].text.value

        # Debug: Print the original message before cleaning
        print("Original Message:", latest_message)

        # Clean the response message by removing source tags
        cleaned_message = re.sub(SOURCE_TAG_PATTERN, '', latest_message)

        # Debug: Print the cleaned message after applying the regex
        print("Cleaned Message:", cleaned_message)

        return jsonify({'response': cleaned_message})

    except Exception as e:
        print(f"Error during chat processing: {str(e)}")
        return jsonify(
            {'response':
             'An error occurred while processing your request.'}), 500


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
