from __future__ import annotations

import json
import pathlib
import re


ROOT = pathlib.Path("/Users/kathy/Documents/vibe coding/ielts-question-bank-test")
SOURCE = ROOT / "data" / "writing_questions.json"
OUT_JSON = ROOT / "docs" / "writing" / "writing_card_core_text_review.json"
OUT_MD = ROOT / "docs" / "writing" / "writing_card_core_text_review.md"


def clean_prompt(prompt: str) -> str:
    text = str(prompt or "").replace("\r", "")
    text = re.sub(r"^WRITING TASK\s*[12]\s*", "", text, flags=re.I)
    text = re.sub(r"You should spend about \d+ minutes on this task\.?", "", text, flags=re.I)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def prompt_lines(prompt: str) -> list[str]:
    lines: list[str] = []
    for raw in clean_prompt(prompt).split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        if re.match(r"^write at least \d+ words", line, flags=re.I):
            continue
        if re.match(r"^you do NOT need to write any addresses", line, flags=re.I):
            continue
        if re.match(r"^begin your letter as follows", line, flags=re.I):
            continue
        if re.match(r"^dear ", line, flags=re.I):
            continue
        lines.append(line)
    return lines


def task1_context(lines: list[str]) -> str:
    pieces: list[str] = []
    for line in lines:
        if re.match(r"^write a letter", line, flags=re.I):
            break
        if re.match(r"^•", line):
            break
        pieces.append(line)
    return " ".join(pieces).strip()


def normalize_phrase(text: str) -> str:
    text = text.strip().rstrip(".")
    text = re.sub(r"\s+", " ", text)
    return text


def extract_task1_core(prompt: str) -> str:
    lines = prompt_lines(prompt)
    context = task1_context(lines)
    low = context.lower()

    patterns = [
        (r"asked you for your feedback.*service", "feedback about the service provided by a removal company"),
        (r"asked you for your feedback on the training course", "feedback on a work training course"),
        (r"invite a famous actor to open a new theatre", "inviting a famous actor to open a new theatre"),
        (r"thinking about spending a year studying abroad", "advice about spending a year studying abroad"),
        (r"organise an event to celebrate this anniversary", "organising a ten-year college reunion celebration"),
        (r"move to a different department in the same company", "requesting a transfer to another department in the same company"),
        (r"wish to stay in the apartment for longer", "asking to extend the rental period for an apartment"),
        (r"popular food from around the world", "recommending a popular dish for an international food event"),
        (r"reduce your working hours in order to study part time", "requesting reduced working hours in order to study part time"),
        (r"bought some train tickets.*staff were very unhelpful", "complaint about train tickets and unhelpful station staff"),
        (r"feedback .* service", "feedback about a service you recently used"),
        (r"invite .* open", "inviting someone to open an event or venue"),
        (r"study abroad", "advice about studying abroad"),
        (r"celebrate this anniversary", "organising a college reunion celebration"),
        (r"different department", "requesting a transfer to another department"),
        (r"rent the apartment for longer", "asking to extend an apartment rental"),
        (r"popular dish", "recommending a dish for an international food event"),
        (r"reduce your working hours", "requesting reduced working hours for part-time study"),
        (r"training course", "feedback on a work training course"),
        (r"train company", "complaint to a train company"),
        (r"manager", "a request to your manager"),
        (r"owner of your apartment", "a request to an apartment owner"),
        (r"friend's sister", "advice to a friend's sister"),
        (r"college friend", "planning a celebration with a college friend"),
    ]
    for pattern, phrase in patterns:
        if re.search(pattern, low):
            return phrase

    context = normalize_phrase(context)
    context = re.sub(r"^you ", "", context, flags=re.I)
    context = context[:1].lower() + context[1:] if context else context
    return context or "task 1 letter purpose"


def extract_task2_core(prompt: str) -> str:
    lines = prompt_lines(prompt)
    content = [
        line
        for line in lines
        if not re.match(r"^write about the following topic", line, flags=re.I)
        and not re.match(r"^give reasons", line, flags=re.I)
        and not re.match(r"^include any relevant examples", line, flags=re.I)
    ]
    statement = next((line for line in content if "?" not in line and not re.match(r"^discuss both views", line, flags=re.I)), "")
    questions = [line for line in content if "?" in line]
    joined = "\n".join(content).lower()

    if "discuss both these views" in joined or "discuss both views" in joined:
        if re.search(r"photograph|photographers|famous people", joined):
            return "Are photographers wrong to follow famous people everywhere they go?"
        if statement:
            return normalize_phrase(statement)

    if any(key in joined for key in ["positive or a negative", "positive or negative", "good thing or a bad thing", "good thing or a bad thing"]):
        for q in questions:
            if re.search(r"positive|negative|good thing|bad thing", q, flags=re.I):
                return normalize_phrase(q)

    if "advantages and disadvantages" in joined or "more advantages than disadvantages" in joined:
        for q in questions:
            if re.search(r"advantages|disadvantages", q, flags=re.I):
                return normalize_phrase(q)

    if "how can" in joined:
        for q in questions:
            if re.search(r"^how can", q, flags=re.I):
                return normalize_phrase(q)

    if "should" in joined:
        for q in questions:
            if re.search(r"^should", q, flags=re.I):
                return normalize_phrase(q)

    if "do you think" in joined or "what's your opinion" in joined or "what is your opinion" in joined:
        for q in questions:
            if re.search(r"do you think|what's your opinion|what is your opinion", q, flags=re.I):
                return normalize_phrase(q)

    if any(key in joined for key in ["why do you think", "what are the reasons", "what are the causes"]):
        if len(questions) >= 2:
            second = normalize_phrase(questions[1])
            if re.search(r"positive|negative|advantages|disadvantages|how can|should", second, flags=re.I):
                return second
        return normalize_phrase(questions[-1] if questions else statement)

    if questions:
        return normalize_phrase(questions[-1])
    return normalize_phrase(statement) or "task 2 core question"


def build_rows() -> list[dict]:
    questions = json.loads(SOURCE.read_text())["questions"]
    rows: list[dict] = []
    for item in questions:
        full_prompt = clean_prompt(item["prompt"])
        core = extract_task1_core(full_prompt) if item["type"] == "task1" else extract_task2_core(full_prompt)
        rows.append(
            {
                "id": item["id"],
                "type": item["type"],
                "source_title": item.get("title", ""),
                "full_prompt": full_prompt,
                "card_core_text": core,
            }
        )
    return rows


def write_outputs(rows: list[dict]) -> None:
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2))

    lines = [
        "# Writing Card Core Text Review",
        "",
        "Review-only draft. This file is not wired into the UI yet.",
        "",
        f"Total items: {len(rows)}",
        "",
    ]
    for section in ("task1", "task2"):
        items = [row for row in rows if row["type"] == section]
        lines.append(f"## {section.upper()} ({len(items)})")
        lines.append("")
        for idx, row in enumerate(items, 1):
            lines.append(f"### {idx}. {row['id']}")
            if row["source_title"]:
                lines.append(f"Source title: `{row['source_title']}`")
            lines.append("Full prompt:")
            lines.append("```text")
            lines.append(row["full_prompt"])
            lines.append("```")
            lines.append(f"Card core text: `{row['card_core_text']}`")
            lines.append("")
    OUT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    rows = build_rows()
    write_outputs(rows)
    print(OUT_MD)
    print(OUT_JSON)
