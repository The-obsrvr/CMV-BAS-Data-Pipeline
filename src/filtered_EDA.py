import json
from collections import Counter, defaultdict
from itertools import combinations


def load_threads(path):
    threads = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            threads.append(json.loads(line))
    return threads


def compute_basic_stats(threads):
    """

    :param threads:
    :return:
    """
    total = len(threads)
    delta = sum(1 for t in threads if t.get("is_delta", False))
    non_delta = total - delta

    return {
        "total_threads": total,
        "delta_threads": delta,
        "non_delta_threads": non_delta
    }


def compute_conversation_stats(threads):
    """
    Compute average turns and sentences for delta vs non-delta conversations.
    Uses pre-computed fields (turn_count, sentence_count) if available,
    otherwise falls back to counting from the conversation list directly.
    """

    def get_turn_count(t):
        if "turn_count" in t:
            return t["turn_count"]
        return sum(1 for turn in t.get("conversation", [])
                   if not turn.get("deleted", False)
                   )

    def get_sentence_count(t):
        if "sentence_count" in t:
            return t["sentence_count"]
        # fallback — requires nltk if not pre-computed
        try:
            from nltk.tokenize import sent_tokenize
            return sum(
                len(sent_tokenize(turn.get("text", "")))
                for turn in t.get("conversation", [])
                if not turn.get("deleted", False)
                )
        except Exception:
            return 0

    delta_threads = [t for t in threads if t.get("is_delta", False)]
    non_delta_threads = [t for t in threads if not t.get("is_delta", False)]

    def averages(group):
        if not group:
            return {"avg_turns": 0.0, "avg_sentences": 0.0, "count": 0}
        turns = [get_turn_count(t) for t in group]
        sentences = [get_sentence_count(t) for t in group]
        return {
            "count": len(group),
            "avg_turns": round(sum(turns) / len(turns), 2),
            "avg_sentences": round(sum(sentences) / len(sentences), 2),
            "min_turns": min(turns),
            "max_turns": max(turns),
            "min_sentences": min(sentences),
            "max_sentences": max(sentences),
            }

    return {
        "delta": averages(delta_threads),
        "non_delta": averages(non_delta_threads),
        "overall": averages(threads),
        }


def split_eu(threads):
    eu_threads = [t for t in threads if t.get("is_eurocentric", False)]
    non_eu_threads = [t for t in threads if not t.get("is_eurocentric", False)]
    return eu_threads, non_eu_threads


def topic_distribution(threads):
    counter = Counter()

    for t in threads:
        topics = t.get("detected_topics", [])
        counter.update(topics)

    return dict(counter)


def print_stats(title, stats):
    print(f"\n===== {title} =====")
    for k, v in stats.items():
        print(f"{k}: {v}")


def print_topic_stats(title, topic_dict):
    print(f"\n===== {title} =====")
    total = sum(topic_dict.values())

    for topic, count in topic_dict.items():
        perc = (count / total * 100) if total > 0 else 0
        print(f"{topic}: {count} ({perc:.2f}%)")


def print_conversation_stats(stats):
    print("\n===== AVERAGE TURNS & SENTENCES (DELTA vs NON-DELTA) =====")
    for group, vals in stats.items():
        print(
            f"\n  {group.upper()} (n={vals['count']})\n"
            f"    Turns     — avg: {vals['avg_turns']:>7.2f}  "
            f"min: {vals['min_turns']:>4}  max: {vals['max_turns']:>4}\n"
            f"    Sentences — avg: {vals['avg_sentences']:>7.2f}  "
            f"min: {vals['min_sentences']:>4}  max: {vals['max_sentences']:>4}"
            )


# UNIQUE TOPICS PER THREAD
def unique_topics_per_thread(threads):
        counts = Counter()

        for t in threads:
            unique_topics = set(t.get("detected_topics", []))
            counts.update(unique_topics)

        return dict(counts)


# DELTA vs TOPIC CORRELATION
def delta_topic_correlation(threads):

        stats = defaultdict(lambda: {"delta": 0, "non_delta": 0, "total": 0})

        for t in threads:
            topics = set(t.get("detected_topics", []))
            is_delta = t.get("is_delta", False)

            for topic in topics:
                stats[topic]["total"] += 1
                if is_delta:
                    stats[topic]["delta"] += 1
                else:
                    stats[topic]["non_delta"] += 1

        # Compute delta rate
        results = {}
        for topic, vals in stats.items():
            total = vals["total"]
            delta_rate = vals["delta"] / total if total > 0 else 0

            results[topic] = {
                "total_threads": total,
                "delta_threads": vals["delta"],
                "non_delta_threads": vals["non_delta"],
                "delta_rate": round(delta_rate, 4)
                }

        return results


# CO-OCCURRENCE MATRIX
def topic_cooccurrence(threads):
        co_matrix = defaultdict(lambda: defaultdict(int))

        for t in threads:
            topics = list(set(t.get("detected_topics", [])))

            for t1, t2 in combinations(topics, 2):
                co_matrix[t1][t2] += 1
                co_matrix[t2][t1] += 1

            # self-count (optional, useful for normalization later)
            for t1 in topics:
                co_matrix[t1][t1] += 1

        return co_matrix


    # -----------------------------
    # PRINT HELPERS
    # -----------------------------
def print_unique_topics(stats):
        print("\n===== UNIQUE TOPICS PER THREAD =====")
        total = sum(stats.values())
        for topic, count in stats.items():
            perc = (count / total * 100) if total else 0
            print(f"{topic}: {count} ({perc:.2f}%)")


def print_delta_correlation(stats):
        print("\n===== DELTA vs TOPIC =====")
        for topic, vals in stats.items():
            print(
                f"{topic} | total: {vals['total_threads']} | "
                f"delta: {vals['delta_threads']} | "
                f"non-delta: {vals['non_delta_threads']} | "
                f"delta_rate: {vals['delta_rate']}"
                )


def print_cooccurrence(matrix):
        print("\n===== CO-OCCURRENCE MATRIX =====")

        topics = sorted(matrix.keys())

        # Header
        print("\t" + "\t".join(topics))

        for t1 in topics:
            row = [str(matrix[t1].get(t2, 0)) for t2 in topics]
            print(f"{t1}\t" + "\t".join(row))



def main(path):

    threads = load_threads(path)


    # OVERALL STATS
    overall_stats = compute_basic_stats(threads)
    print_stats("OVERALL", overall_stats)

    overall_topics = topic_distribution(threads)
    print_topic_stats("TOPIC DISTRIBUTION (OVERALL)", overall_topics)

    conv_stats = compute_conversation_stats(threads)
    print_conversation_stats(conv_stats)

    # EU SPLIT
    eu_threads, non_eu_threads = split_eu(threads)

    eu_stats = compute_basic_stats(eu_threads)
    non_eu_stats = compute_basic_stats(non_eu_threads)

    print_stats("EU THREADS", eu_stats)
    print_stats("NON-EU THREADS", non_eu_stats)

    # TOPIC DISTRIBUTION BY GROUP
    eu_topics = topic_distribution(eu_threads)
    non_eu_topics = topic_distribution(non_eu_threads)

    print_topic_stats("TOPIC DISTRIBUTION (EU)", eu_topics)
    print_topic_stats("TOPIC DISTRIBUTION (NON-EU)", non_eu_topics)


    # ---- UNIQUE TOPICS ----
    unique_stats = unique_topics_per_thread(threads)
    print_unique_topics(unique_stats)

    # ---- DELTA CORRELATION ----
    delta_stats = delta_topic_correlation(threads)
    print_delta_correlation(delta_stats)

    # ---- CO-OCCURRENCE ----
    co_matrix = topic_cooccurrence(threads)
    print_cooccurrence(co_matrix)


if __name__ == "__main__":
    main("Data/raw/filtered_threads.jsonl")



