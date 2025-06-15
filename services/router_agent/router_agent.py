import os
import json
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

AGENT_URLS = {
    "KnowledgeAgent": "http://knowledge:8000/handle_request",  
    "CustomerSupportAgent": "http://customer-support:8000/handle_request",
    "GeneralAgent": "http://general:8000/handle_request",  
    "PersonalityLayer": "http://personality:8000/handle_request"  
}

# AGENT_URLS = {
#     "KnowledgeAgent": "http://localhost:8003/handle_request",  
#     "CustomerSupportAgent": "http://localhost:8001/handle_request",
#     "GeneralAgent": "http://localhost:8002/handle_request",  
#     "PersonalityLayer": "http://localhost:8004/handle_request"  
# }

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RouterAgent:
    def __init__(self):
        self.agent_prompt_path = "shared/prompts/router_agent_prompt.txt"

    def decide_agent(self, user_input):
        system_prompt = load_prompt_template(self.agent_prompt_path)
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        }
        try:
            logger.info(f"Sending user input to LLM for agent decision: {user_input}")
            resp = requests.post(API_ENDPOINT, headers=HEADERS, json=payload)
            resp.raise_for_status()
            response = resp.json()
            agent_name = response["choices"][0]["message"]["content"].strip()
            logger.info(f"Chosen agent: {agent_name}")
            return agent_name if agent_name in AGENT_URLS else "KnowledgeAgent"
        except Exception as e:
            logger.error(f"[Router Error] {e}")
            return "KnowledgeAgent"  # Default fallback

    def run(self, user_id, user_input):
        chosen_agent_name = self.decide_agent(user_input)
        agent_url = AGENT_URLS.get(chosen_agent_name, AGENT_URLS["GeneralAgent"])

        payload = {"user_id": user_id, "message": user_input}

        try:
            logger.info(f"Sending request to {chosen_agent_name} at {agent_url}")
            response = requests.post(agent_url, json=payload)
            response.raise_for_status()
            agent_response = response.json()

            agent_workflow = [{"agent_name": "RouterAgent", "tool_calls": {"LLM": chosen_agent_name}}]
            tool_output = agent_response.get("Response", "")
            agent_workflow.append([{
                "agent_name": chosen_agent_name,
                "tool_calls": {"llm_response": tool_output}
            }])

            logger.info("Sending response to PersonalityLayer for further processing")
            personality_response = requests.post(AGENT_URLS["PersonalityLayer"], json={"raw_response": tool_output, "question": user_input})
            final_response = personality_response.json()

            agent_workflow.append({
                "agent_name": "PersonalityLayer",
                "tool_calls": {"LLM": final_response}
            })

            logger.info(f"Returning final response: {final_response}")

            return {
                "response": final_response,
                "source_agent_response": tool_output,
                "agent_workflow": agent_workflow
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {"error": f"Error calling {chosen_agent_name}: {str(e)}"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"error": "Error decoding response from agent"}

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": "An unexpected error occurred"}
