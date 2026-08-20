import json
import os
from dotenv import load_dotenv
from google import genai
import re
import logging

from app.database import get_promoted_categories

load_dotenv()

logger = logging.getLogger(__name__)

OFFICIAL_CATEGORIES = [
    "Technical Support",
    "Product Support",
    "Customer Service",
    "IT Support",
    "Billing and Payments",
    "Returns and Exchanges",
    "Service Outages and Maintenance",
    "Sales and Pre-Sales",
    "Human Resources",
    "General Inquiry",
]

OFFICIAL_PRIORITIES = ["Low", "Medium", "High", "Urgent"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-flash-lite")


def _extract_json_payload(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in Gemini response.")

    json_text = text[start:end + 1]
    return json.loads(json_text)


def _validate_gemini_response(data: dict, categories: list[str]) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Gemini response JSON must be an object.")

    decision = data.get("decision")
    category = data.get("category")
    reason = data.get("reason")

    if decision not in {"existing", "new"}:
        raise ValueError("Gemini response decision must be 'existing' or 'new'.")

    if not isinstance(category, str) or not category.strip():
        raise ValueError("Gemini response category must be a non-empty string.")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Gemini response reason must be a non-empty string.")

    if decision == "existing" and category not in categories:
        raise ValueError("Gemini response returned an existing decision with an unknown category.")

    if decision == "new" and category in categories:
        raise ValueError("Gemini response returned a new decision with an official category.")

    return {
        "decision": decision,
        "category": category.strip(),
        "reason": reason.strip(),
    }


def get_current_official_categories() -> list[str]:
    """Return the current official category list.

    This includes the original Random Forest categories plus any promoted pending categories.
    """
    promoted = get_promoted_categories()
    promoted_names = [row["category_name"] for row in promoted]
    combined = OFFICIAL_CATEGORIES + [name for name in promoted_names if name not in OFFICIAL_CATEGORIES]
    return combined


def _validate_gemini_priority_response(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Gemini response JSON must be an object.")

    priority = data.get("priority")
    reason = data.get("reason")

    if not isinstance(priority, str) or not priority.strip():
        raise ValueError("Gemini response priority must be a non-empty string.")

    if priority.strip() not in OFFICIAL_PRIORITIES:
        raise ValueError("Gemini response priority must be one of the official priority levels.")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Gemini response reason must be a non-empty string.")

    return {
        "priority": priority.strip(),
        "reason": reason.strip(),
    }


def mask_pii(text: str) -> str:
    """Mask obvious PII in a complaint copy before sending to Gemini.

    Rules (non-destructive to original input):
    - Emails -> [EMAIL]
    - Phone numbers (10-digit patterns, common separators, optional +cc) -> [PHONE]
    - Card numbers (13-19 digits, spaces/hyphens allowed) -> [CARD_NUMBER]
    - Aadhaar-like 12-digit numbers -> [ID_NUMBER]
    - Labeled IDs (Order ID, Account Number, Customer ID) -> replace value with bracketed token

    Uses only Python stdlib `re` and avoids aggressive masking of ordinary numbers.
    """
    try:
        masked = text

        # 1) Labeled identifiers (replace only the value portion)
        labeled_patterns = [
            (re.compile(r"(?i)(Order\s*(?:ID)?\s*[:#]?\s*)([A-Z0-9-]+)"), r"\1[ORDER_ID]"),
            (re.compile(r"(?i)(Account\s*(?:Number)?\s*[:#]?\s*)([A-Z0-9-]+)"), r"\1[ACCOUNT_NUMBER]"),
            (re.compile(r"(?i)(Customer\s*(?:ID)?\s*[:#]?\s*)([A-Z0-9-]+)"), r"\1[CUSTOMER_ID]"),
        ]
        for pat, repl in labeled_patterns:
            masked = pat.sub(repl, masked)

        # 2) Credit/debit card numbers (13-19 digits, allow spaces or hyphens)
        card_pat = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
        masked = card_pat.sub("[CARD_NUMBER]", masked)

        # 3) Aadhaar-like 12-digit numbers (allow spaces)
        aadhaar_pat = re.compile(r"(?<!\d)(?:\d[ -]?){12}(?!\d)")
        masked = aadhaar_pat.sub("[ID_NUMBER]", masked)

        # 4) Phone numbers: common 10-digit patterns and international +cc variants
        #    Match patterns like 9876543210, 987-654-3210, 987 654 3210, +1-987-654-3210, +91 9876543210
        phone_patterns = [
            re.compile(r"(?<!\d)(?:\d{10})(?!\d)"),
            re.compile(r"(?<!\w)(?:\+\d{1,3}[\s-]?(?:\d{3}[\s-]?\d{3}[\s-]?\d{4}))(?!\w)"),
            re.compile(r"(?<!\d)(?:\d{3}[\s-]?\d{3}[\s-]?\d{4})(?!\d)"),
        ]
        for p in phone_patterns:
            masked = p.sub("[PHONE]", masked)

        # 5) Email addresses
        email_pat = re.compile(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}")
        masked = email_pat.sub("[EMAIL]", masked)

        # If any masking occurred, log a privacy-friendly message
        if masked != text:
            logger.info("[PII] Complaint text masked before Gemini")

        return masked
    except Exception:
        # Fail-safe: do not raise — caller will handle Gemini fallback errors
        logger.exception("PII masking failed; proceeding without masking")
        return text


def gemini_classify_priority(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Complaint text must be a non-empty string.")

    # Mask PII before sending to Gemini
    masked_text = mask_pii(text)

    prompt_text = (
        "You are a complaint priority classification assistant.\n\n"
        "Your task is to classify the complaint into the most appropriate priority level.\n\n"
        "Use only the complaint title and description. Do not infer urgency from the user's writing style, emotion, rudeness, or threats alone.\n\n"
        "Focus on the actual impact, severity, time sensitivity, service disruption, financial impact, safety implications, and number of people potentially affected.\n\n"
        "Urgent should be used only when the complaint clearly indicates an immediate or critical issue requiring immediate attention.\n"
        "High should be used for serious issues that require prompt attention but are not clearly immediate emergencies.\n"
        "Medium should be used for normal issues requiring attention without strong urgency.\n"
        "Low should be used for minor, informational, non-critical, or convenience-related issues.\n\n"
        "Do not invent facts that are not present in the complaint. If the complaint does not contain enough information for high urgency, prefer Medium rather than assuming High or Urgent.\n\n"
        "Return strictly valid JSON only, with no markdown, no code fences, and no additional text.\n"
        "The JSON must include exactly these keys: priority, reason.\n"
        "The priority value must be exactly one of: Low, Medium, High, Urgent.\n\n"
        "Respond with this exact format:\n"
        "{\n"
        "  \"priority\": \"High\",\n"
        "  \"reason\": \"The complaint describes a serious service issue that requires prompt attention.\"\n"
        "}\n\n"
        "Complaint:\n"
        f"{masked_text.strip()}"
    )

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt_text,
        config={"temperature": 0.0, "max_output_tokens": 512},
    )

    output_text = getattr(response, "text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        output_text = "".join(
            getattr(part, "text", "")
            for part in getattr(response, "parts", [])
            if getattr(part, "text", None)
        )

    if not isinstance(output_text, str) or not output_text.strip():
        raise RuntimeError("Gemini returned an unexpected response format.")

    parsed = _extract_json_payload(output_text)
    return _validate_gemini_priority_response(parsed)


def gemini_classify_complaint(text: str, categories: list[str]) -> dict:
    if not text or not text.strip():
        raise ValueError("Complaint text must be a non-empty string.")

    if not categories:
        raise ValueError("Category list cannot be empty.")

    # Mask PII before sending to Gemini
    masked_text = mask_pii(text)

    categories_list = "\n".join(f"- {category}" for category in categories)
    prompt_text = (
       "You are a complaint categorization assistant.\n\n"

"Your task is to classify the complaint into the most appropriate category.\n\n"

"FIRST, carefully understand the meaning and intent of the entire complaint. "
"Do not classify based only on individual keywords.\n\n"

"Prefer an existing official category whenever the complaint genuinely fits its meaning, "
"even if the complaint is worded differently from typical examples of that category.\n\n"

"Only propose a new category when the complaint represents a genuinely different type of issue "
"that cannot reasonably fit any official category. "
"Do not create a new category merely because the wording, product, or situation is different.\n\n"

"Official categories:\n"
f"{categories_list}\n\n"

"Category rules:\n"
"1. Choose an existing category when its meaning clearly matches the complaint.\n"
"2. Consider the full complaint context, not isolated keywords.\n"
"3. Do not invent a new category when an existing category is a reasonable semantic match.\n"
"4. Propose a new category only when none of the official categories adequately represent the complaint.\n"
"5. New category names must be short, clear, meaningful, and consistent with the style of the official categories.\n"
"6. Do not create categories for minor wording differences or variations of the same underlying issue.\n\n"

"Return strictly valid JSON only, with no markdown, no code fences, and no additional text.\n"
"The JSON must include exactly these keys: decision, category, reason.\n"
"The decision must be either \"existing\" or \"new\".\n\n"

"Respond with one of these exact formats:\n"
"{\n"
"  \"decision\": \"existing\",\n"
"  \"category\": \"Technical Support\",\n"
"  \"reason\": \"The complaint concerns a technical problem that fits the existing Technical Support category.\"\n"
"}\n"
"or\n"
"{\n"
"  \"decision\": \"new\",\n"
"  \"category\": \"Account Security\",\n"
"  \"reason\": \"The complaint describes a distinct issue that does not reasonably fit any official category.\"\n"
"}\n\n"

"Complaint:\n"
        f"{masked_text.strip()}"
    )

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt_text,
        config={"temperature": 0.0, "max_output_tokens": 512},
    )

    output_text = getattr(response, "text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        output_text = "".join(
            getattr(part, "text", "")
            for part in getattr(response, "parts", [])
            if getattr(part, "text", None)
        )

    if not isinstance(output_text, str) or not output_text.strip():
        raise RuntimeError("Gemini returned an unexpected response format.")

    parsed = _extract_json_payload(output_text)
    return _validate_gemini_response(parsed, categories)
