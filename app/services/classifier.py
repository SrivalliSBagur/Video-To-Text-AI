import anthropic
import json
from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CONTENT_TYPES = ["recipe", "coding", "educational", "general", "music"]

def classify_content(transcript: str) -> dict:
    preview = transcript[:3000]

    prompt = f"""You are a content classifier. Read the transcript below and classify it into exactly one of these categories:

- recipe: cooking, food preparation, ingredients, how to make a dish
- coding: programming tutorials, code walkthroughs, software development, tech demos
- educational: explanations of concepts, lectures, how-things-work videos, science, history, finance, self help
- music: song lyrics, music videos, concerts, performances, anything where the main content is a song being sung
- general: anything else — entertainment, vlogs, news, sports, podcasts

Transcript:
{preview}

Respond in this exact JSON format and nothing else:
{{
  "content_type": "<one of: recipe, coding, educational, music, general>",
  "confidence": "<high, medium, or low>",
  "reason": "<one sentence explaining why>"
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(response_text)

        if result.get("content_type") not in CONTENT_TYPES:
            result["content_type"] = "general"

        return {"success": True, **result}

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content_type": "general",
            "confidence": "low",
            "reason": "Classification failed, defaulting to general"
        }