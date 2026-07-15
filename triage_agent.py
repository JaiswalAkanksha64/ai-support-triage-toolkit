import json
import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


def load_tickets():
    """Reads all tickets from the data file and returns them as a Python list."""
    with open("data/tickets.json", "r", encoding="utf-8") as f:
        tickets = json.load(f)
    return tickets

def load_knowledge_base():
    """
    Reads all knowledge-base docs and returns a dictionary
    mapping product name -> doc content.
    """
    product_docs = {
        "DataBridge Pro": "data/knowledge-base/products/databridge-pro.md",
        "CloudSync": "data/knowledge-base/products/cloudsync.md",
        "AnalyticsHub": "data/knowledge-base/products/analyticshub.md",
        "SecureVault": "data/knowledge-base/products/securevault.md",
        "WorkflowEngine": "data/knowledge-base/products/workflowengine.md",
    }

    kb = {}
    for product_name, filepath in product_docs.items():
        with open(filepath, "r", encoding="utf-8") as f:
            kb[product_name] = f.read()

    return kb


def find_relevant_doc(ticket, knowledge_base):
    """
    Given a ticket, returns the matching knowledge-base doc content,
    or None if no match found.
    """
    product = ticket.get("product")
    return knowledge_base.get(product)

def triage_ticket(ticket, knowledge_base, max_retries=2):
    """
    Sends one ticket to the AI model and asks it to classify it,
    recommend a team, and draft a first response.
    Retries automatically if the AI returns malformed JSON.
    Returns a Python dictionary (parsed from the AI's JSON response).
    """
    relevant_doc = find_relevant_doc(ticket, knowledge_base)
    doc_context = relevant_doc if relevant_doc else "No matching knowledge base doc found."

    prompt = f"""You are a support ticket triage assistant for a B2B software company.

Read the following support ticket and analyze it.

Subject: {ticket['subject']}
Body: {ticket['body']}
Product: {ticket['product']}

Here is the relevant knowledge base doc for this product:
---
{doc_context}
---

Respond ONLY with a JSON object in this exact structure, no extra text:
{{
  "product_area": "string",
  "category": "one of: Bug, Feature Request, How-To, Performance, Billing, Integration, Onboarding, Data Loss",
  "urgency": "one of: P1, P2, P3, P4",
  "reasoning": "1-2 sentence explanation of your classification",
  "recommended_team": "one of: Tier-1 Support, Tier-2 Engineering, Billing Team, Product Team, Onboarding Team",
  "draft_response": "A short, polite first-response message (3-4 sentences) a support agent could send to the customer, acknowledging their issue and next steps",
  "kb_doc_referenced": "true or false depending on whether the knowledge base content was relevant and used"
}}
"""

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
             model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError as e:
            last_error = e
            print(f"  [Retry {attempt + 1}/{max_retries}] JSON parse failed, retrying...")
        except Exception as e:
            last_error = e
            print(f"  [Retry {attempt + 1}/{max_retries}] API error ({e}), waiting before retry...")
            time.sleep(5)

    # If all retries failed, return a fallback structure instead of crashing
    return {
        "product_area": "PARSE_ERROR",
        "category": "Bug",
        "urgency": "P3",
        "reasoning": f"Failed to parse AI response after {max_retries} retries: {last_error}",
        "recommended_team": "Tier-1 Support",
        "draft_response": "Unable to generate response due to a processing error.",
        "kb_doc_referenced": "false"
    }


if __name__ == "__main__":
    tickets = load_tickets()
    knowledge_base = load_knowledge_base()
    first_ticket = tickets[3]

    print("Sending this ticket to the triage agent:")
    print(f"Subject: {first_ticket['subject']}\n")

    result = triage_ticket(first_ticket, knowledge_base)

    print("Triage agent result:\n")
    print(json.dumps(result, indent=2))