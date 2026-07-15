import json
import os
import time
from dotenv import load_dotenv
from groq import Groq

from triage_agent import load_tickets, load_knowledge_base, triage_ticket
from account_summarizer import load_accounts, summarize_account

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

MODEL_NAME = "llama-3.3-70b-versatile"
CACHE_FILE = "eval_cache.json"

VALID_CATEGORIES = ["Bug", "Feature Request", "How-To", "Performance", "Billing", "Integration", "Onboarding", "Data Loss"]
VALID_URGENCY = ["P1", "P2", "P3", "P4"]
VALID_TEAMS = ["Tier-1 Support", "Tier-2 Engineering", "Billing Team", "Product Team", "Onboarding Team"]


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def rule_based_check_triage(result):
    issues = []
    required_fields = ["product_area", "category", "urgency", "reasoning", "recommended_team", "draft_response"]

    for field in required_fields:
        if field not in result:
            issues.append(f"Missing field: {field}")

    if result.get("category") not in VALID_CATEGORIES:
        issues.append(f"Invalid category: {result.get('category')}")

    if result.get("urgency") not in VALID_URGENCY:
        issues.append(f"Invalid urgency: {result.get('urgency')}")

    if result.get("recommended_team") not in VALID_TEAMS:
        issues.append(f"Invalid team: {result.get('recommended_team')}")

    if not result.get("draft_response") or len(result.get("draft_response", "")) < 20:
        issues.append("draft_response missing or too short")

    passed = len(issues) == 0
    return passed, issues


def llm_judge_triage(ticket, result):
    judge_prompt = f"""You are grading an AI support-triage system's output.

Original ticket:
Subject: {ticket['subject']}
Body: {ticket['body']}

The AI produced this classification:
{json.dumps(result, indent=2)}

Judge whether this classification is reasonable given the ticket content.
Consider: is the category sensible, is the urgency justified, is the draft response
appropriate and professional?

Respond ONLY with JSON: {{"score": 0.0 to 1.0, "justification": "1 sentence"}}
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": judge_prompt}],
        response_format={"type": "json_object"},
        temperature=0
    )
    judged = json.loads(response.choices[0].message.content)
    return judged["score"], judged["justification"]


def run_triage_eval(cache):
    tickets = load_tickets()
    knowledge_base = load_knowledge_base()

    test_indices = {
        0: "Normal case - feature request mislabeled as Billing in source data",
        3: "Tricky case - CHECKSUM_MISMATCH error requiring KB knowledge",
        475: "ADVERSARIAL - vague onboarding question, minimal detail",
    }

    results = []
    for idx, description in test_indices.items():
        ticket = tickets[idx]
        cache_key = f"triage_{ticket['ticket_id']}"

        if cache_key in cache:
            print(f"  {ticket['ticket_id']}: using cached result")
            results.append(cache[cache_key])
            continue

        triage_result = triage_ticket(ticket, knowledge_base)
        rule_passed, rule_issues = rule_based_check_triage(triage_result)
        score, justification = llm_judge_triage(ticket, triage_result)

        entry = {
            "ticket_id": ticket["ticket_id"],
            "description": description,
            "rule_based_passed": rule_passed,
            "rule_based_issues": rule_issues,
            "llm_judge_score": score,
            "llm_judge_justification": justification,
            "output": triage_result,
        }

        cache[cache_key] = entry
        save_cache(cache)

        results.append(entry)
        print(f"  {ticket['ticket_id']}: rules={'PASS' if rule_passed else 'FAIL'}, quality_score={score}")
        time.sleep(2)

    return results


def run_account_eval(cache):
    accounts = load_accounts()
    tickets = load_tickets()

    test_account_ids = [
        accounts[0]["account_id"],
        accounts[1]["account_id"],
        "ACC-9999",
    ]

    results = []
    for acc_id in test_account_ids:
        cache_key = f"account_{acc_id}"

        if cache_key in cache:
            print(f"  {acc_id}: using cached result")
            results.append(cache[cache_key])
            continue

        summary = summarize_account(acc_id, accounts, tickets)

        if "error" in summary:
            passed = acc_id == "ACC-9999"
            entry = {
                "account_id": acc_id,
                "rule_based_passed": passed,
                "note": "Correctly handled missing account" if passed else "Unexpected error",
                "output": summary,
            }
        else:
            required_fields = ["executive_summary", "risks_and_flags", "recommended_talking_points"]
            issues = [f"Missing {f}" for f in required_fields if f not in summary]
            passed = len(issues) == 0
            entry = {
                "account_id": acc_id,
                "rule_based_passed": passed,
                "rule_based_issues": issues,
                "output": summary,
            }

        cache[cache_key] = entry
        save_cache(cache)

        results.append(entry)
        print(f"  {acc_id}: rules={'PASS' if entry['rule_based_passed'] else 'FAIL'}")
        time.sleep(2)

    return results


if __name__ == "__main__":
    cache = load_cache()

    print("Running Task 1 eval (triage agent)...")
    triage_results = run_triage_eval(cache)

    print("\nRunning Task 2 eval (account summarizer)...")
    account_results = run_account_eval(cache)

    report = {
        "task1_triage_eval": triage_results,
        "task2_account_eval": account_results,
    }

    with open("eval_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\nDone. Full report saved to eval_report.json")