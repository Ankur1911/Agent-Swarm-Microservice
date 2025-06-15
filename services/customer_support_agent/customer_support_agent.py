import os
import json
import sqlite3
import requests
import numpy as np
from sentence_transformers import SentenceTransformer, util
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import logging


from shared.utils.load_prompt import load_prompt_template
from shared.utils.tools import db_query, contact_support

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# get environment variables for API access
API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY       = os.getenv("API_KEY")

#get environment variables for email support
support_email = os.getenv("SUPPORT_EMAIL")
smtp_server = os.getenv("SMTP_SERVER")  
smtp_port = os.getenv("SMTP_PORT") 
sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")

# List of FAQs (Dummy data for testing)
faq_list = [
    {"question": "How can I Contact Support?", "answer": "You can contact support by support@example.com"},
    {"question": "How do I reset my password?", "answer": "You can reset your password by going to the settings page and clicking on 'Reset Password'."},
    {"question": "What is policy on refunds?", "answer": "Our refund policy allows you to request a refund within 30 days of purchase if you are not satisfied with the product."}
]

def get_faq_questions() -> list:
    return [f["question"] for f in faq_list]

def lookup_faq_answer(question: str) -> str:
    for f in faq_list:
        if f["question"] == question:
            return f["answer"]
    return "No answer available for this question."


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_data (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    user_name TEXT,
    payment_status TEXT,
    order_status TEXT
);
"""

def init_db():
    conn = sqlite3.connect(":memory:")   # Using in-memory database for testing
    cur = conn.cursor()
    cur.execute(DB_SCHEMA)
    cur.executemany(
        "INSERT OR IGNORE INTO user_data VALUES (?,?,?,?,?);",
        [
            ("client789","c789@example.com","John Doe","Paid","Shipped"),
            ("client790","c790@example.com","Jane Doe","Pending","Processing")
        ]
    )
    conn.commit()
    logger.info("Database initialized with user data.")
    return conn

# db_query function to retrieve a single field for a user from the database
def db_query_tool(conn, user_id: str, field: str) -> str:
    logger.info(f"Querying database for user_id: {user_id}")    
    cur = conn.cursor()
    
    cur.execute(
        "SELECT {} FROM user_data WHERE user_id=?;".format(field),
        (user_id,)
    )
    row = cur.fetchone()

    return row[0] if row and row[0] is not None else "Not found"

# contact_support function to send an email to support team
def contact_support_tool(user_id: str, question: str) -> str:
    logger.info(f"Sending support request for user {user_id} with question: {question}")    
    # Create the email content
    subject = f"Support Request from User {user_id}"
    body = f"""
    Hello Support Team,
    
    User ID: {user_id}
    Question: {question}
    
    Please assist the user with the query above.
    
    Best regards,
    Your Support System
    """
    
    # Create the MIME message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = support_email
    message["Subject"] = subject
    
    # Attach the body to the email
    message.attach(MIMEText(body, "plain"))
    
    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)  
            server.sendmail(sender_email, support_email, message.as_string())  # Send the email
        logger.info(f"Slack notification sent to support team for user {user_id}.")
        return f"Our support team will contact you soon regarding your question: “{question}” (user: {user_id})."
    
    except Exception as e:
        logger.error(f"Error occurred while sending the email: {e}")
        return f"An error occurred while sending the email: {str(e)}"        


HEADERS = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

# Tools definition
TOOLS = [db_query, contact_support]

# SupportAgent class to handle customer support queries
class SupportAgent:
    def __init__(self, threshold: float = 0.7):
        self.conn = init_db()
        self.model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
        self.threshold = threshold
        self.prompt_template_path = "shared/prompts/customer_support_prompt.txt"

    # Function to find the most similar FAQ question    
    def _most_similar_faq(self, question: str):
        faqs = get_faq_questions()
        q_emb = self.model.encode(question)
        f_embs = self.model.encode(faqs)
        sims = util.pytorch_cos_sim(q_emb, f_embs).numpy()[0]
        idx = int(np.argmax(sims))
        return (faqs[idx], sims[idx]) if sims[idx] > self.threshold else (None, 0)

    def handle(self, user_id: str, question: str) -> str:
        # 1. FAQ check
        matched, score = self._most_similar_faq(question)
        if matched:
            logger.info("Found matching FAQ")
            return {"tool_name":"faq_answer","Response":lookup_faq_answer(matched)}

        system_prompt = load_prompt_template(self.prompt_template_path)

        # 2. Tool calling via OpenAI API
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User {user_id} asks: {question}"}
            ],
            "tools": TOOLS,
            "tool_choice": "auto"
        }

        try:
            logger.info("Sending request to OpenAI API for support query processing.")
            resp = requests.post(
                API_ENDPOINT,
                headers=HEADERS,
                json=payload
            )
            resp.raise_for_status()
            response_data = resp.json()
            
            message = response_data["choices"][0]["message"]
            
            # Check if the model wants to use tools
            if message.get("tool_calls"):
                tool_call = message["tool_calls"][0] 
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                
                # Execute the appropriate function
                if function_name == "db_query_tool":
                    result = db_query_tool(self.conn,**function_args)
                elif function_name == "contact_support_tool":
                    result = contact_support_tool(**function_args)
                else:
                    result = "Unknown tool called"
                
                return {"tool_name":function_name,"Response":result}
            
            # If no tool calls, return the regular response
            elif message.get("content"):
                return {"tool_name":"llm_response","Response": message["content"]}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return "Sorry, there was an error processing your request."
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return "Sorry, there was an error processing the response."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "Sorry, an unexpected error occurred."

        # Fallback if nothing worked
        logger.warning("Fallback triggered, no data found.")
        return "No data found"
