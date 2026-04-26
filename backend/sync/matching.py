import difflib
import unicodedata
from collections.abc import Mapping, Sequence
from typing import NotRequired, TypedDict


class PlayerNameData(TypedDict):
    notion_id: str
    name: str
    alias: list[str]


class PlayerSimilarityDict(TypedDict):
    notion_id: str
    notion_name: str
    snapshot: str
    similarity: float
    match_method: str
    matched_alias: NotRequired[str | None]
    existing_local_name: NotRequired[str | None]


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: remove accents, lowercase, strip, collapse whitespace."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8")
    return " ".join(name.lower().split())


def words_match(word_a: str, word_b: str) -> float:
    """Check similarity between two words using difflib."""
    if not word_a or not word_b:
        return 0.0

    wa = word_a.lower().rstrip(".")
    wb = word_b.lower().rstrip(".")

    if wa == wb:
        return 1.0

    if len(wa) >= 1 and len(wb) >= 1 and (wb.startswith(wa) or wa.startswith(wb)):
        return 0.8

    return difflib.SequenceMatcher(None, wa, wb).ratio()


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two names (0.0 to 1.0)."""
    norm_a = normalize_name(a)
    norm_b = normalize_name(b)

    if not norm_a and not norm_b:
        return 1.0
    if not norm_a or not norm_b:
        return 0.0

    words_a = norm_a.split()
    words_b = norm_b.split()

    short_words = words_a if len(words_a) <= len(words_b) else words_b
    long_words = words_b if len(words_a) <= len(words_b) else words_a

    matched_count = 0.0
    used_long_indices: set[int] = set()

    for sw in short_words:
        best_word_sim = 0.0
        best_idx = -1
        for i, lw in enumerate(long_words):
            if i in used_long_indices:
                continue
            sim = words_match(sw, lw)
            if sim > best_word_sim:
                best_word_sim = sim
                best_idx = i

        if best_word_sim >= 0.85:
            matched_count += 1.0
            used_long_indices.add(best_idx)
        elif best_word_sim >= 0.5:
            matched_count += best_word_sim
            used_long_indices.add(best_idx)

    score = matched_count / len(long_words)
    best_score = score

    if matched_count == len(short_words) and len(long_words) - len(short_words) == 1:
        best_score = max(best_score, 0.8)

    # Boost if the shorter name is highly matched but the longer name has extra words/abbreviations
    # E.g., "Eduardo G." (matched_count ~ 1.8) vs "Eduardo Gonzalez-Prada Arriaran" (3 words)
    if len(short_words) >= 2 and matched_count >= len(short_words) - 0.25:
        # Boost the score, but penalize slightly for missing long words
        subset_score = matched_count / len(short_words)
        boosted = subset_score * 0.85
        best_score = max(best_score, boosted)

    return best_score


def detect_similar_names(
    notion_players: Mapping[str, PlayerNameData] | Sequence[PlayerNameData],
    snapshot_names: list[str],
    threshold: float = 0.75,
) -> list[PlayerSimilarityDict]:
    players_list = (
        list(notion_players.values()) if isinstance(notion_players, Mapping) else notion_players
    )
    norm_snapshots = {name: normalize_name(name) for name in snapshot_names}
    potential_matches: list[PlayerSimilarityDict] = []

    exact_matches_snapshot: set[str] = set()
    claimed_notion_ids: set[str] = set()

    for player_data in players_list:
        notion_main_name = player_data["name"]
        norm_notion_main = normalize_name(notion_main_name)
        notion_id = player_data["notion_id"]

        for snap_name in snapshot_names:
            if norm_notion_main == norm_snapshots[snap_name]:
                exact_matches_snapshot.add(snap_name)
                claimed_notion_ids.add(notion_id)  # Reclamamos este ID
                continue

    for player_data in players_list:
        notion_id = player_data["notion_id"]

        if notion_id in claimed_notion_ids:
            continue

        notion_main_name = player_data["name"]
        notion_variations = [notion_main_name] + player_data.get("alias", [])

        for snap_name in snapshot_names:
            if snap_name in exact_matches_snapshot:
                continue

            best_sim = 0.0
            best_match_method = "fuzzy"
            matched_alias: str | None = None

            for var in notion_variations:
                sim = similarity(normalize_name(var), norm_snapshots[snap_name])
                if sim > best_sim:
                    best_sim = sim
                    if var != notion_main_name:
                        matched_alias = var
                        best_match_method = "alias_exact" if sim == 1.0 else "alias_fuzzy"
                    else:
                        best_match_method = "name_fuzzy"

            if best_sim >= threshold:
                match_data: PlayerSimilarityDict = {
                    "notion_id": notion_id,
                    "notion_name": notion_main_name,
                    "snapshot": snap_name,
                    "similarity": round(best_sim, 3),
                    "match_method": best_match_method,
                }
                if matched_alias:
                    match_data["matched_alias"] = matched_alias
                potential_matches.append(match_data)

    unique_matches: list[PlayerSimilarityDict] = []
    seen: set[tuple[str, str]] = set()
    for m in potential_matches:
        key = (m["notion_name"], m["snapshot"])
        if key not in seen:
            unique_matches.append(m)
            seen.add(key)

    unique_matches.sort(key=lambda x: x["similarity"], reverse=True)
    return unique_matches
