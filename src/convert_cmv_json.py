import json
import re
import sys


# ── helpers ──────────────────────────────────────────────────────────────────

# Matches "!delta" or the delta/triangle unicode characters (Δ, ∆)
DELTA_MARKER_RE = re.compile(r'(!delta|[Δ∆])', re.IGNORECASE)


def contains_delta_marker(text: str) -> bool:
    """Return True if the comment body contains a delta award marker."""
    return bool(DELTA_MARKER_RE.search(text))


def has_explanation(text: str) -> bool:
    """
    A valid delta award must include a short explanation beyond the marker.
    We require at least ~10 non-whitespace characters outside the marker itself
    to distinguish a genuine explanation from a bare '!delta' or 'Δ'.
    """
    stripped = DELTA_MARKER_RE.sub('', text).strip()
    return len(stripped) >= 10


def is_delta_award(body: str, author: str, op_author: str) -> bool:
    """
    Return True when this comment is an OP delta-award comment:
      - authored by the OP
      - contains a delta marker (Δ, ∆, or !delta)
      - contains an explanation (not just the bare marker)
    """
    return (
        author == op_author
        and contains_delta_marker(body)
        and has_explanation(body)
    )


def clean_text(text: str) -> str:
    """Remove non-ASCII chars, URLs, emojis and other non-textual objects."""
    # replace reddit block-quotes ("> ...") with "previously stated: ..."
    text = re.sub(r'(?m)^&gt;\s*(.*)', r'previously stated: "\1"', text)
    # strip URLs
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    # remove non-ASCII (covers emojis, special unicode)
    text = text.encode('ascii', 'ignore').decode('ascii')
    # collapse excess blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def is_deleted(comment: dict) -> bool:
    return (
        comment.get('body', '') in ('[deleted]', '[removed]', '')
        or comment.get('author', '') in ('[deleted]', '[removed]')
    )


def count_sentences(text: str) -> int:
    """Rough sentence count via punctuation boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return max(1, len([s for s in sentences if s]))


# ── pseudonym registry ────────────────────────────────────────────────────────

class PseudonymRegistry:
    def __init__(self):
        self._map: dict[str, str] = {}
        self._counter = 0

    def get(self, username: str) -> str:
        if username in ('[deleted]', '[removed]', ''):
            return 'deleted_user'
        if username not in self._map:
            self._counter += 1
            self._map[username] = f'Speaker {self._counter}'
        return self._map[username]


# ── delta-event scanner ───────────────────────────────────────────────────────

def find_delta_cutoff(comments: list, op_author: str):
    """
    Walk the full comment tree and return the timestamp of the earliest
    comment in which the OP awards a delta (contains marker + explanation).
    Returns None if no delta award is found.
    """
    earliest = None

    def scan(comment_list):
        nonlocal earliest
        for c in comment_list:
            body   = c.get('body', '')
            author = c.get('author', '')
            if is_delta_award(body, author, op_author):
                ts = float(c.get('created_utc', 0))
                if earliest is None or ts < earliest:
                    earliest = ts
            scan(c.get('children', []))

    scan(comments)
    return earliest


# ── depth-first traversal ─────────────────────────────────────────────────────

def traverse(comment, parent_speaker, registry, result, cutoff_ts, sentence_budget):
    """Recursively traverse a comment tree depth-first."""

    ts = float(comment.get('created_utc', 0))

    # delta thread: drop comments at or after the delta event timestamp
    if cutoff_ts is not None and ts >= cutoff_ts:
        return

    speaker = registry.get(comment.get('author', ''))
    deleted = is_deleted(comment)
    body    = 'deleted' if deleted else clean_text(comment.get('body', ''))

    # non-delta thread: enforce 500-sentence cap
    if cutoff_ts is None and not deleted:
        if sentence_budget[0] <= 0:
            return
        sentence_budget[0] -= count_sentences(body)
        # include this comment even if it pushes the budget below 0

    tag = (
        f'[{speaker} replying to {parent_speaker}]'
        if parent_speaker else
        f'[{speaker}]'
    )

    result.append({
        'post_id':    comment['id'],
        'parent_id':  comment.get('parent_id', ''),
        'conv_id':    comment.get('link_id', ''),
        'speaker_id': speaker,
        'timestamp':  comment.get('created_utc', ''),
        'text':       f'{tag}: {body}',
        'deleted':    deleted,
    })

    next_parent = speaker if not deleted else parent_speaker
    for child in comment.get('children', []):
        traverse(child, next_parent, registry, result, cutoff_ts, sentence_budget)


# ── main converter ────────────────────────────────────────────────────────────

def convert(raw: dict) -> list:
    """
    Convert one raw submission into a list of datapoints — one per top-level
    comment branch.

    Structure of each datapoint:
      OP post  →  top-level comment  →  its full subtree (depth-first)

    A single registry is shared across all branches of the same submission so
    that a speaker who appears in multiple branches receives the same pseudonym.

    Delta detection is performed once across the entire submission tree.
    The resulting cutoff timestamp applies uniformly to every branch:
    - Delta branches   : comments at or after cutoff_ts are dropped.
    - Non-delta branches: a fresh 500-sentence budget is applied per branch.
    """
    registry   = PseudonymRegistry()          # shared across all branches
    op_author  = raw.get('author', '[deleted]')
    op_speaker = registry.get(op_author)
    comments   = raw.get('comments', [])

    # ── delta detection (scans the entire tree once) ──────────────────────────
    cutoff_ts  = find_delta_cutoff(comments, op_author)
    delta_hint = raw.get('delta', False)
    is_delta   = delta_hint or (cutoff_ts is not None)
    # effective_cutoff is None for non-delta (or unresolvable delta → keep all)
    effective_cutoff = cutoff_ts

    # ── shared OP entry (prepended to every branch) ───────────────────────────
    op_text = clean_text(raw.get('selftext', '') or raw.get('title', ''))
    op_entry = {
        'post_id':    raw['id'],
        'parent_id':  '',
        'conv_id':    raw['id'],
        'speaker_id': op_speaker,
        'timestamp':  raw.get('created_utc', ''),
        'text':       f'[{op_speaker} - Original Post]: {op_text}',
        'deleted':    False,
    }

    # ── one datapoint per top-level comment ───────────────────────────────────
    datapoints = []
    for idx, top_comment in enumerate(comments):
        branch: list = [op_entry]                 # always start with the OP
        sentence_budget = [500]                   # fresh budget per branch

        traverse(
            top_comment,
            op_speaker,
            registry,
            branch,
            effective_cutoff,
            sentence_budget,
        )

        # Skip branches that contain only the OP entry (e.g. the top-level
        # comment was filtered out entirely by the delta cutoff).
        if len(branch) == 1:
            continue

        # Each branch gets a unique thread_id: <submission_id>_<branch_index>
        thread_id = f'{raw["id"]}_{idx}'

        # A branch is a delta thread only if it contains the delta-award comment
        # (i.e. the award comment's timestamp falls within this branch's window).
        branch_is_delta = is_delta and effective_cutoff is not None

        datapoints.append({
            'thread_id':    thread_id,
            'conv_id':      raw['id'],
            'title':        raw.get('title', ''),
            'is_delta':     branch_is_delta,
            'delta_ts':     cutoff_ts,
            'subreddit':    raw.get('subreddit', ''),
            'conversation': branch,
        })

    return datapoints


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _is_jsonl(path: str) -> bool:
    """Infer format from extension; .jsonl / .ndjson → True, else False."""
    return path.lower().endswith(('.jsonl', '.ndjson'))


def process_json(input_path: str, output_path: str) -> None:
    """Read a single JSON file (object or array) and write pretty JSON output."""
    with open(input_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    submissions = raw if isinstance(raw, list) else [raw]
    datapoints  = [dp for submission in submissions for dp in convert(submission)]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(datapoints, f, ensure_ascii=False, indent=2)

    print(f'Done. {len(datapoints)} thread(s) from {len(submissions)} submission(s) '
          f'written to {output_path}')


def process_jsonl(input_path: str, output_path: str) -> None:
    """
    Read a JSONL file (one JSON submission per line), split each submission
    into one datapoint per top-level comment branch, and write each datapoint
    as its own line in the output JSONL file.

    - Blank lines are skipped.
    - Lines that fail to parse or convert are logged and skipped so a single
      bad record does not abort the entire run.
    """
    submissions_ok = submissions_skipped = threads_written = 0

    with (
        open(input_path,  'r', encoding='utf-8') as fin,
        open(output_path, 'w', encoding='utf-8') as fout,
    ):
        for lineno, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f'  [WARN] line {lineno}: JSON parse error — {exc}', file=sys.stderr)
                submissions_skipped += 1
                continue

            try:
                datapoints = convert(raw)
            except Exception as exc:
                print(f'  [WARN] line {lineno}: conversion error — {exc}', file=sys.stderr)
                submissions_skipped += 1
                continue

            for dp in datapoints:
                fout.write(json.dumps(dp, ensure_ascii=False) + '\n')
                threads_written += 1

            submissions_ok += 1
            if submissions_ok % 500 == 0:
                print(f'  … {submissions_ok} submissions processed '
                      f'({threads_written} threads written)', file=sys.stderr)

    print(
        f'Done. {submissions_ok} submission(s) → {threads_written} thread(s) '
        f'written to {output_path}'
        + (f', {submissions_skipped} submission(s) skipped due to errors.'
           if submissions_skipped else '.')
    )


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert raw CMV JSON/JSONL to flattened paragraph format.'
    )
    parser.add_argument('--input',  help='Input file (.json or .jsonl/.ndjson)')
    parser.add_argument('--output', help='Output file (.json or .jsonl/.ndjson)')
    parser.add_argument(
        '--format',
        choices=['json', 'jsonl'],
        default='jsonl',
        help='Force input/output format (default: inferred from file extension)',
    )
    args = parser.parse_args()

    # Determine format: explicit flag wins, otherwise infer from input extension
    if args.format == 'jsonl' or (args.format is None and _is_jsonl(args.input)):
        process_jsonl(args.input, args.output)
    else:
        process_json(args.input, args.output)


if __name__ == '__main__':
    main()
