# AI Support Triage Toolkit

An AI-powered toolkit for support ticket triage and customer account health summarization, built for technical support and account management teams.

## Features

- **Triage Agent**: Classifies incoming support tickets (product area, category, urgency), matches relevant knowledge-base documentation, recommends a responder team, and drafts a first-response message.
- **Account Health Summarizer**: Generates a 3-part account health brief (executive summary, risks & flags, talking points) from account data and ticket history, with evidence-based churn risk flagging.
- **Evaluation Harness**: Automated testing combining rule-based structural checks and LLM-as-judge quality scoring across both agents.

## Setup

1. Clone this repo and navigate into it:

git clone https://github.com/JaiswalAkanksha64/ai-support-triage-toolkit.git
cd ai-support-triage-toolkit

2. Create and activate a virtual environment:

python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

3. Install dependencies:

pip install -r requirements.txt

4. Copy `.env.example` to `.env` and add your Groq API key (free at console.groq.com):

GROQ_API_KEY=your_key_here

## Usage

**Run the triage agent on a sample ticket:**

python triage_agent.py

**Run the account health summarizer on a sample account:**

python account_summarizer.py

**Run the full evaluation suite:**

python eval_harness.py

This generates `eval_report.json` with pass/fail results and quality scores across test cases for both agents.

## Design Note

See [DESIGN_NOTE.md](./DESIGN_NOTE.md) for failure modes, latency/quality trade-offs, data sensitivity, and scaling considerations.

## Tech Stack

- Python 3.13
- Groq API (Llama 3.3 70B) for LLM inference
- python-dotenv for secrets management

Step 4: Create .env.example (shows what env vars are needed, without real values — required by the task rules)

GROQ_API_KEY=your_groq_api_key_here