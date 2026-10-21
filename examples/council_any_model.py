"""council_any_model.py - run the council kit with real models behind it. Each brain is two functions you supply; here both call a model through openai_compat.

Run with the kits on PYTHONPATH (see USE_IN_VS_CODE.md), and set the key variables for the models you use. To try it with no model at all, run:  python council_any_model.py --demo
"""
import pathlib
import sys
import tempfile

from vega_council.deliberation import Brain, Council
from vega_custody.dag.dag import Dag

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from openai_compat import make_asker


def model_brain(brain_id, family, ask):
    def answer(prompt):
        return ask(prompt)

    def review(prompt, others, own_label):
        stances = []
        for label, text in others.items():
            verdict = ask("Question:\n%s\n\nAnother answer:\n%s\n\nReply with exactly one word: VALIDATE, CHALLENGE or EXTEND." % (prompt, text)).strip().upper()
            word = verdict.split()[0].strip(".,:;") if verdict else "EXTEND"
            stances.append({"stance": word if word in ("VALIDATE", "CHALLENGE", "EXTEND") else "EXTEND", "target": label, "note": "reviewed by " + brain_id})
        return stances
    return Brain(brain_id, family, answer, review)


def demo_ask(name):
    return lambda p: "VALIDATE" if p.startswith("Question:") else "Paris is the capital of France. (%s)" % name


def main():
    if "--demo" in sys.argv:
        brains = [model_brain("a", "fam-a", demo_ask("a")), model_brain("b", "fam-b", demo_ask("b")), model_brain("c", "fam-c", demo_ask("c"))]
    else:
        brains = [model_brain("openrouter-1", "family-one", make_asker("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "REPLACE-WITH-A-MODEL-NAME")),
                  model_brain("local-1", "family-two", make_asker("http://localhost:11434/v1", "", "REPLACE-WITH-A-LOCAL-MODEL"))]
    t = pathlib.Path(tempfile.mkdtemp())
    council = Council(brains, Dag([t / "c.jsonl"], [t / "l.jsonl"]))
    result = council.deliberate("What is the capital of France?")
    print(result["outcome"], "| winner:", result["winner"], "| dissent:", len(result["dissent"]))


if __name__ == "__main__":
    main()
