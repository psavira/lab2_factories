import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services.email_topic_inference import EmailTopicInferenceService
from app.dataclasses import Email

TOPICS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'topic_keywords.json')
EMAILS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'emails.json')

router = APIRouter()

class EmailRequest(BaseModel):
    subject: str
    body: str

class EmailWithTopicRequest(BaseModel):
    subject: str
    body: str
    topic: str

class EmailClassificationResponse(BaseModel):
    predicted_topic: str
    topic_scores: Dict[str, float]
    features: Dict[str, Any]
    available_topics: List[str]

class EmailAddResponse(BaseModel):
    message: str
    email_id: int

class StoreEmailRequest(BaseModel):
    subject: str
    body: str
    ground_truth: Optional[str] = None

class TopicRequest(BaseModel):
    name: str
    description: str

class TopicResponse(BaseModel):
    message: str
    topic: str
    topics: List[str]

@router.post("/emails/classify", response_model=EmailClassificationResponse)
async def classify_email(request: EmailRequest):
    try:
        inference_service = EmailTopicInferenceService()
        email = Email(subject=request.subject, body=request.body)
        result = inference_service.classify_email(email)
        
        return EmailClassificationResponse(
            predicted_topic=result["predicted_topic"],
            topic_scores=result["topic_scores"],
            features=result["features"],
            available_topics=result["available_topics"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topics")
async def topics():
    """Get available email topics"""
    inference_service = EmailTopicInferenceService()
    info = inference_service.get_pipeline_info()
    return {"topics": info["available_topics"]}

@router.post("/emails", response_model=EmailAddResponse, status_code=201)
async def store_email(request: StoreEmailRequest):
    """Store an email with an optional ground truth topic label."""
    try:
        if request.ground_truth is not None:
            with open(TOPICS_FILE, 'r') as f:
                known_topics = json.load(f)
            if request.ground_truth not in known_topics:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown ground truth topic '{request.ground_truth}'. Valid topics: {list(known_topics.keys())}"
                )

        with open(EMAILS_FILE, 'r') as f:
            emails = json.load(f)

        email_id = len(emails) + 1
        emails.append({
            "id": email_id,
            "subject": request.subject,
            "body": request.body,
            "ground_truth": request.ground_truth,
        })

        with open(EMAILS_FILE, 'w') as f:
            json.dump(emails, f, indent=2)

        return EmailAddResponse(message="Email stored successfully", email_id=email_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pipeline/info") 
async def pipeline_info():
    inference_service = EmailTopicInferenceService()
    return inference_service.get_pipeline_info()

@router.post("/topics", response_model=TopicResponse, status_code=201)
async def add_topic(request: TopicRequest):
    """Add a new topic to the classification system and persist it to disk."""
    try:
        with open(TOPICS_FILE, 'r') as f:
            topics = json.load(f)

        if request.name in topics:
            raise HTTPException(status_code=409, detail=f"Topic '{request.name}' already exists")

        topics[request.name] = {"description": request.description}

        with open(TOPICS_FILE, 'w') as f:
            json.dump(topics, f, indent=2)

        return TopicResponse(
            message=f"Topic '{request.name}' added successfully",
            topic=request.name,
            topics=list(topics.keys())
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# TODO: LAB ASSIGNMENT - Part 2 of 2  
# Create a GET endpoint at "/features" that returns information about all feature generators
# available in the system.
#
# Requirements:
# 1. Create a GET endpoint at "/features"
# 2. Import FeatureGeneratorFactory from app.features.factory
# 3. Use FeatureGeneratorFactory.get_available_generators() to get generator info
# 4. Return a JSON response with the available generators and their feature names
# 5. Handle any exceptions with appropriate HTTP error responses
#
# Expected response format:
# {
#   "available_generators": [
#     {
#       "name": "spam",
#       "features": ["has_spam_words"]
#     },
#     ...
#   ]
# }
#
# Hint: Look at the existing endpoints above for patterns on error handling
# Hint: You may need to instantiate generators to get their feature names

