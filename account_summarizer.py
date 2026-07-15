import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


def load_accounts():
    """Reads all accounts from the data file and returns them as a Python list."""
    with open("data/accounts.json", "r", encoding="utf-8") as f:
        accounts = json.load(f)
    return accounts


def load_tickets():
    """Reads all tickets from the data file and returns them as a Python list."""
    with open("data/tickets.json", "r", encoding="utf-8") as f:
        tickets = json.load(f)
    return tickets


def get_account_by_id(account_id, accounts):
    """Finds and returns one account matching the given account_id, or None."""
    for account in accounts:
        if account["account_id"] == account_id:
            return account
    return None


def get_tickets_for_account(account_id, tickets):
    """Returns a list of all tickets belonging to the given account_id."""
    return [t for t in tickets if t.get("account_id") == account_id]


def summarize_account(account_id, accounts, tickets):
    """
    Generates a 3-section account health brief for the given account_id.
    Returns a Python dictionary parsed from the AI's JSON response.
    """
    account = get_account_by_id(account_id, accounts)
    if account is None:
        return {"error": f"No account found with ID {account_id}"}

    account_tickets = get_tickets_for_account(account_id, tickets)

    tickets_text = ""
    for t in account_tickets:
        tickets_text += f"- [{t['urgency']}] {t['subject']}: {t['body'][:200]}\n"

    if not tickets_text:
        tickets_text = "No tickets on record for this account."

    prompt = f"""You are a TAM (Technical Account Manager) assistant preparing an account brief for a QBR (Quarterly Business Review).

Account data:
{json.dumps(account, indent=2)}

Recent tickets for this account:
{tickets_text}

Write a structured account health brief with exactly 3 sections. Pay close attention to escalation_notes
even if they seem to conflict with structured fields - unstructured notes often contain the most recent,
specific signals. Any churn risk you flag MUST include a direct quote from a ticket or escalation note as justification.

Respond ONLY with a JSON object in this exact structure, no extra text:
{{
  "executive_summary": "3-5 sentence overview of this account's overall status",
  "risks_and_flags": [
    {{"risk": "short description", "evidence_quote": "direct quote from ticket or escalation note supporting this"}}
  ],
  "recommended_talking_points": ["point 1", "point 2", "point 3"]
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0
    )

    result = json.loads(response.choices[0].message.content)
    return result


if __name__ == "__main__":
    accounts = load_accounts()
    tickets = load_tickets()

    test_account_id = accounts[0]["account_id"]

    print(f"Generating health brief for account: {test_account_id}\n")

    result = summarize_account(test_account_id, accounts, tickets)

    print(json.dumps(result, indent=2))