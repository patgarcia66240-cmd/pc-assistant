"""Chat handler for image generation plugin in ARIA.

Intercepts natural language requests to create/generate images across Chat and Voice Assistant modes,
extracting prompt instructions and navigating to the image generator plugin with auto-execution.
"""
import re

IMAGE_MATCH_PATTERNS = [
    r"\b(?:g[ée]n[èe]re|g[ée]n[ée]rer|cr[ée]e|cr[ée]er|fais|faire|dessine|dessiner|peins|peindre|produis|produire)\b.*?\b(?:image|illustration|dessin|visuel|photo|tableau)\b",
    r"\b(?:fais|g[ée]n[èe]re|cr[ée]e|dessine)[\s-]moi\b.*?\b(?:image|illustration|dessin|visuel|photo|tableau)\b",
    r"\b(?:une|un)\s+(?:image|illustration|dessin)\s+(?:de|d['’]|avec|pour|repr[ée]sentant)\b",
    r"\bje\s+(?:voudrais|veux|souhaite)\s+(?:une|un)\s+(?:image|illustration|dessin)\b",
    r"\bpeux-?tu\s+(?:me\s+)?(?:faire|cr[ée]er|g[ée]n[èe]rer|dessiner|peindre)\s+(?:une|un)\s+(?:image|illustration)\b",
]

COMPILED_MATCHERS = [re.compile(pattern, re.IGNORECASE) for pattern in IMAGE_MATCH_PATTERNS]


def matches(message: str) -> bool:
    if not message or not message.strip():
        return False
    return any(matcher.search(message) for matcher in COMPILED_MATCHERS)


def extract_prompt(message: str) -> str:
    cleaned = message.strip()

    cleaned = re.sub(
        r"\b(?:s['’]il\s+te\s+pla[îi]t|stp|s['’]il\s+vous\s+pla[îi]t|svp|merci)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip(" ,.!?")

    prefix_pattern = re.compile(
        r"^(?:"
        r"(?:peux-?tu|pourrais-?tu)\s+(?:me\s+)?(?:faire|cr[ée]er|g[ée]n[èe]rer|dessiner|peindre)\s+(?:une|un)\s+(?:image|illustration|dessin|visuel|photo|tableau)\s*(?:de|d['’]|avec|pour|repr[ée]sentant|:)?|"
        r"je\s+(?:voudrais|veux|souhaite)\s+(?:une|un)\s+(?:image|illustration|dessin|visuel|photo|tableau)\s*(?:de|d['’]|avec|pour|repr[ée]sentant|:)?|"
        r"(?:g[ée]n[èe]re|g[ée]n[ée]rer|cr[ée]e|cr[ée]er|fais|faire|dessine|dessiner|peins|peindre|produis|produire)[\s-]*(?:moi)?\s+(?:une|un)\s+(?:image|illustration|dessin|visuel|photo|tableau)\s*(?:de|d['’]|avec|pour|repr[ée]sentant|:)?|"
        r"(?:g[ée]n[èe]re|g[ée]n[ée]rer|cr[ée]e|cr[ée]er|fais|faire|dessine|dessiner|peins|peindre|produis|produire)[\s-]*(?:moi)?\s+(?:de|d['’]|avec|pour|:)?|"
        r"(?:une|un)?\s*(?:image|illustration|dessin)\s*(?:de|d['’]|avec|pour|repr[ée]sentant|:)"
        r")\s*",
        re.IGNORECASE,
    )

    prompt = prefix_pattern.sub("", cleaned).strip(" :.,!?\"'«»")

    if prompt:
        prompt = prompt[0].upper() + prompt[1:]
    return prompt


async def handle(message: str, context: dict) -> dict:
    prompt = extract_prompt(message)
    if prompt:
        response_text = f"Je lance la création de l’image : « {prompt} »."
    else:
        response_text = "Redirection vers le générateur d’images."

    return {
        "response": response_text,
        "data": {
            "navigate_to": "image_generation",
            "prompt": prompt,
            "auto_submit": bool(prompt),
        },
        "source": "local",
        "source_type": "image_generation",
    }
