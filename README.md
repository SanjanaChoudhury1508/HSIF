# HSIF - Human State Intelligence Framework for Conversational AI

> A Human State Intelligence Framework that enables conversational AI systems to understand human conversational states and adapt their responses intelligently in real time.

---

# Project Overview

Traditional conversational AI systems primarily rely on:

- Speech-to-Text (STT)
- Large Language Models (LLMs)
- Tool Calling
- Text-to-Speech (TTS)

Although modern voice assistants may detect basic emotions or sentiment, these signals rarely influence the reasoning process of the AI.

HSIF introduces a **Human State Representation (HSR)** layer between speech processing and the LLM.

Instead of understanding only *what* a user says, the framework also understands **how they are saying it**.

The framework estimates:

- Emotion
- Hesitation
- Confidence
- Engagement
- Cognitive Load
- Intent Continuation
- Interruptibility

These states are fused into a single Human State Representation which guides the dialogue policy before the request reaches the LLM.

---

# High Level Architecture

```
                  User Voice
                       │
                       ▼
          Speech Processing Pipeline
        (VAD + STT + Feature Extraction)
                       │
                       ▼
            Human State Engine
       (Emotion, Confidence, Hesitation,
        Engagement, Cognitive Load)
                       │
                       ▼
        Human State Representation (HSR)
                       │
                       ▼
          Dialogue Policy Engine
                       │
                       ▼
            Backend API Layer
                       │
                       ▼
              Voice Agent / LLM
                       │
                       ▼
                  AI Response
```

---

# Repository Structure

```
HSIF/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── utils/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── ai/
│   │
│   ├── speech/
│   │   ├── preprocessing/
│   │   ├── vad/
│   │   ├── whisper/
│   │   ├── feature_extraction/
│   │   └── speech_service.py
│   │
│   ├── human_state/
│   │   ├── emotion/
│   │   ├── hesitation/
│   │   ├── confidence/
│   │   ├── engagement/
│   │   ├── cognitive_load/
│   │   └── hsr.py
│   │
│   └── dialogue/
│       ├── fusion/
│       ├── policy/
│       ├── memory/
│       ├── prompts/
│       └── dialogue_service.py
│
├── datasets/
│
├── models/
│
├── docs/
│
├── docker/
│
├── tests/
│
├── database/
│
├── .gitignore
│
├── README.md
│
└── docker-compose.yml
```

---

# Team Responsibilities

---

## Member 1 - Speech Processing

Responsible for:

- Audio preprocessing
- Voice Activity Detection (VAD)
- Whisper Speech-to-Text
- Feature Extraction

Working Folder

```
ai/speech/
```

Expected Output

```
Audio
     ↓
Transcript
```

Example

```json
{
   "transcript":"I don't understand this concept..."
}
```

---

## Member 2 - Human State Engine

Responsible for

- Emotion Detection
- Hesitation Detection
- Confidence Estimation
- Engagement Prediction
- Cognitive Load Prediction
- Human State Representation generation

Working Folder

```
ai/human_state/
```

Input

```
Transcript
```

Output

```json
{
   "emotion":"confused",
   "confidence":0.42,
   "hesitation":0.81,
   "engagement":0.93
}
```

---

## Member 3 - Dialogue Policy Engine

Responsible for

- State Fusion
- Dialogue Policy
- Conversation Memory
- Adaptive Response Generation
- Prompt Engineering
- LLM Integration

Working Folder

```
ai/dialogue/
```

Input

```json
{
   "emotion":"confused",
   "confidence":0.42,
   "hesitation":0.81
}
```

Output

```json
{
   "recommended_strategy":"clarify"
}
```

---

## Member 4 - Backend & Integration

Responsible for

- FastAPI Backend
- REST APIs
- Database
- SDK
- Docker
- Testing
- Integration

Working Folder

```
backend/
```

---

# Development Workflow

Every member should work only inside their assigned folder.

Avoid modifying another member's module unless discussed.

---

# Git Workflow

## Step 1

Repository Owner creates repository.

```
HSIF
```

---

## Step 2

Repository Owner pushes initial folder structure.

```
git init

git add .

git commit -m "Initial Project Structure"

git push origin main
```

---

## Step 3

Repository Owner adds all members as Collaborators.

GitHub

Settings

↓

Collaborators

↓

Invite Team Members

---

## Step 4

Every member clones the repository.

```
git clone https://github.com/username/HSIF.git
```

---

## Step 5

Create a Feature Branch

Never work directly on **main**

Example

```
feature/speech

feature/human-state

feature/dialogue

feature/backend
```

Create branch

```
git checkout -b feature/speech
```

---

## Step 6

Develop your module.

Commit regularly.

```
git add .

git commit -m "Implemented Whisper pipeline"
```

Push

```
git push origin feature/speech
```

---

## Step 7

Open Pull Request.

GitHub

↓

Compare

↓

Pull Request

↓

Request Review

---

## Step 8

Repository Owner reviews code.

Merge only after testing.

---

## Step 9

Everyone updates local repository.

```
git checkout main

git pull origin main
```

---

# Branch Naming Convention

Speech Module

```
feature/speech
```

Human State Engine

```
feature/human-state
```

Dialogue Engine

```
feature/dialogue
```

Backend

```
feature/backend
```

Bug Fixes

```
fix/backend

fix/dialogue
```

Documentation

```
docs/readme
```

---

# Coding Standards

- Write meaningful variable names.
- Comment important logic.
- Follow PEP-8 (Python).
- Use modular code.
- Avoid hardcoding values.
- Push small commits frequently.

---

# Project Timeline

## Week 1

### Speech Team

- Install Whisper
- Audio preprocessing
- Voice Activity Detection
- Feature Extraction

Deliverable

Audio → Transcript

---

### Human State Team

- Emotion Detection
- Confidence
- Hesitation
- Engagement

Deliverable

Transcript → HSR JSON

---

### Dialogue Team

- State Fusion
- Rule-based Policy Engine
- Prompt Templates

Deliverable

HSR → Strategy

---

### Backend Team

- FastAPI
- PostgreSQL
- REST APIs
- Swagger
- Docker

Deliverable

Working APIs

---

## Week 2

Integrate all modules.

Pipeline

```
Audio

↓

Transcript

↓

Human State

↓

Dialogue Policy

↓

Backend

↓

JSON Response
```

Test using

- Swagger

or

- Postman

---

# Review 1 Deliverables

The following should be demonstrated during the first review.

✔ Project Architecture

✔ Folder Structure

✔ Git Repository

✔ FastAPI Backend

✔ Speech Processing Prototype

✔ Human State Engine Prototype

✔ Dialogue Policy Prototype

✔ End-to-End Integration

✔ API Demonstration

---

# Tech Stack

Backend

- FastAPI

Database

- PostgreSQL

Speech Recognition

- Faster Whisper

Machine Learning

- PyTorch

- Hugging Face

Deployment

- Docker

Streaming

- WebSockets

Version Control

- Git

API Documentation

- Swagger UI

---

# Long-Term Goal

The final system should support

Audio

↓

Speech Processing

↓

Human State Detection

↓

Dialogue Strategy Recommendation

↓

LLM

↓

Adaptive AI Response

in real time.

---

# Team Rules

✅ One feature branch per member

✅ Never commit directly to main

✅ Pull latest changes before starting work

```
git pull origin main
```

✅ Push code frequently

✅ Resolve merge conflicts before opening PR

✅ Keep README updated

---

Happy Coding 