"""openai_compat.py - one small function that talks to ANY model server that speaks the common "chat completions" format.

That covers OpenRouter, a local OmniRoute gateway, Ollama (its /v1 endpoint), LM Studio, and other providers that offer an OpenAI-compatible endpoint (check each provider's docs for
its exact base URL and model names). The key is read from an environment variable you name, or from nothing for local servers. Only the standard library is used.

    ask = make_asker("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "some/model-name")
    print(ask("Say hello."))
"""
import json
import os
import urllib.request


def make_asker(base_url, key_env, model, timeout=60):
    def ask(prompt):
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(key_env, "") if key_env else ""
        if key:
            headers["Authorization"] = "Bearer " + key
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]
    return ask
