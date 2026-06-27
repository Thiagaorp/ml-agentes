"""Integração com a API do Claude — usada por todos os agentes."""
import json
import re

import anthropic

import config


def perguntar(system, prompt, max_tokens=3000, model=None):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=model or config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def perguntar_json(system, prompt, max_tokens=3000, model=None):
    """Pergunta exigindo resposta em JSON e faz o parse."""
    texto = perguntar(
        system + " Responda APENAS com JSON válido, sem nenhum texto fora do JSON.",
        prompt, max_tokens, model,
    )
    texto = re.sub(r"^```(json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    return json.loads(texto)
