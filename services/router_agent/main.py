from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from services.router_agent.router_agent import RouterAgent
from contextlib import asynccontextmanager

app = FastAPI()

class QuestionRequest(BaseModel):
    user_id: str
    message: str

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ankur1911.github.io/","http://agent-swarm-frontend1.s3-website-us-east-1.amazonaws.com/","*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = RouterAgent()
    app.state.agent = agent
    yield
    
app.state.agent = None  

app = FastAPI(lifespan=lifespan)  

@app.post("/ask")
async def handle_support_request(request: QuestionRequest):
    agent = app.state.agent  
    if not agent:
        return {"error": "Agent not initialized"}
    
    response = agent.run(request.user_id, request.message)
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)