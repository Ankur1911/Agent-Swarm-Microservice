import os
import requests
import logging
from dotenv import load_dotenv
from shared.utils.load_prompt import load_prompt_template

load_dotenv()

API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY = os.getenv("API_KEY")

HEADERS = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonalityLayer:
    def __init__(self):
        self.personality_prompt_path = "shared/prompts/personality_layer_prompt.txt"

    def run(self, raw_response, Question):
        # Format the prompt with the raw response and the user's question
        prompt = load_prompt_template(self.personality_prompt_path)
        prompt = prompt.format(raw_response=raw_response, user_message=Question)

        payload = {
            "messages": [
                {"role": "user", "content": prompt},
            ]
        }

        try:
            logger.info("Sending request to LLM for personality layer processing.")
            resp = requests.post(API_ENDPOINT, headers=HEADERS, json=payload)
            resp.raise_for_status()
            
            final_resp = resp.json()

            # Extract the response from the LLM
            final_response = final_resp["choices"][0]["message"]["content"]
            logger.info(f"Received final response from LLM: {final_response}")

            return final_response
        except requests.exceptions.RequestException as e:
            logger.error(f"[Personality Error] Request failed: {e}")
            return raw_response
        except Exception as e:
            logger.error(f"[Personality Error] Unexpected error: {e}")
            return raw_response