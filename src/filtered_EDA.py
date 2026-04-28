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


 # -----------------------------


    # -----------------------------
    # UNIQUE TOPICS PER THREAD
    # -----------------------------
def unique_topics_per_thread(threads):
        counts = Counter()

        for t in threads:
            unique_topics = set(t.get("detected_topics", []))
            counts.update(unique_topics)

        return dict(counts)


    # -----------------------------
    # DELTA vs TOPIC CORRELATION
    # -----------------------------
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


    # -----------------------------
    # CO-OCCURRENCE MATRIX
    # -----------------------------
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

    # -----------------------------
    # OVERALL STATS
    # -----------------------------
    overall_stats = compute_basic_stats(threads)
    print_stats("OVERALL", overall_stats)

    overall_topics = topic_distribution(threads)
    print_topic_stats("TOPIC DISTRIBUTION (OVERALL)", overall_topics)

    # -----------------------------
    # EU SPLIT
    # -----------------------------
    eu_threads, non_eu_threads = split_eu(threads)

    eu_stats = compute_basic_stats(eu_threads)
    non_eu_stats = compute_basic_stats(non_eu_threads)

    print_stats("EU THREADS", eu_stats)
    print_stats("NON-EU THREADS", non_eu_stats)

    # -----------------------------
    # TOPIC DISTRIBUTION BY GROUP
    # -----------------------------
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



