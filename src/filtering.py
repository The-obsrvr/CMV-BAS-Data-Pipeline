# System Imports
import json
# Third Party Imports
from tqdm import tqdm
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# CONFIG - tunable
MIN_SENTENCES = 30
MIN_TURNS     = 5
SIM_THRESHOLD = 0.40

TOPIC_LABELS = {
    "migration": "immigration, refugees, asylum seekers, border policy",
    "climate": "climate change, global warming, carbon emissions, environment",
    "health": "healthcare systems, hospitals, public health policy",
    "european_integration": "European Union, EU policy, eurozone, Schengen area"
}

EURO_QUERY = "Europe, European countries, EU politics, eurozone"


# LOAD MODEL
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Loaded SentenceTransformer.")
# Precompute embeddings
topic_embeddings = {
    topic: model.encode(desc, convert_to_numpy=True)
    for topic, desc in TOPIC_LABELS.items()
}

euro_embedding = model.encode(EURO_QUERY, convert_to_numpy=True)


# Helper FUNCTIONS
def count_sentences(conversation):
    total = 0
    for turn in conversation:
        if turn.get("deleted", False):
            continue
        total += len(sent_tokenize(turn.get("text", "")))
    return total


def count_turns(conversation):
    """Count non-deleted turns in a conversation."""
    return sum(1 for turn in conversation if not turn.get("deleted", False))


def aggregate_text(conversation):
    return " ".join(
        turn.get("text", "")
        for turn in conversation
        if not turn.get("deleted", False)
    )


def detect_topics_sbert(text):
    text_emb = model.encode(text, convert_to_numpy=True).reshape(1, -1)

    detected = []

    for topic, topic_emb in topic_embeddings.items():
        sim = cosine_similarity(text_emb, topic_emb.reshape(1, -1))[0][0]
        if sim >= SIM_THRESHOLD:
            detected.append(topic)

    return detected


def is_eurocentric_sbert(text):
    text_emb = model.encode(text, convert_to_numpy=True).reshape(1, -1)
    sim = cosine_similarity(text_emb, euro_embedding.reshape(1, -1))[0][0]
    return sim >= SIM_THRESHOLD


def to_serializable(obj):
    """
    Address possible type errors
    :param obj:
    :return:
    """
    import numpy as np

    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()

    raise TypeError(f"Type {type(obj)} not serializable")


def process_jsonl(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(output_path, "w", encoding="utf-8") as out_f:
        for line in tqdm(lines, desc="Processing threads"):
            thread = json.loads(line)
            conversation = thread.get("conversation", [])

            # ---- LENGTH FILTER (min. sentences in thread) ----
            sentence_count = count_sentences(conversation)
            if sentence_count < MIN_SENTENCES:
                continue

            # ---- TURN FILTER (min. turns in thread) ----
            turn_count = count_turns(conversation)
            if turn_count < MIN_TURNS:
                continue

            # ---- SEMANTIC FILTER (political issues) ----
            full_text = aggregate_text(conversation)
            topics = detect_topics_sbert(full_text)

            if not topics:
                continue

            # ---- ADD FIELDS ----
            thread["sentence_count"] = sentence_count
            thread["turn_count"]     = turn_count
            thread["detected_topics"] = [str(t) for t in topics]
            thread["is_eurocentric"] = bool(is_eurocentric_sbert(full_text))

            # ---- WRITE ----
            out_f.write(json.dumps(thread, default=to_serializable) + "\n")

    print("Filtering complete.")


if __name__ == "__main__":
    process_jsonl(
        input_path="Data/raw/outputs.jsonl",
        output_path="Data/raw/filtered_threads.jsonl"
    )