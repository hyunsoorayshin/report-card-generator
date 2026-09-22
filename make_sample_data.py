#!/usr/bin/env python3
"""Generate a synthetic summary CSV in the format report_card.py expects.

The format is the summary written by the desk-tools grade summariser:

    반명, 원생명, Level, Status, 주, Test Count, <subject columns...>,
    Track A Average, Track B Average, Total Average

with section header rows such as

    === 주2 (8명) === Cutline: Lv2: 80 / Lv3: 70 / Lv4: 60

Every name and score here is invented. Students are built from simple
"archetypes" so that each of the six learner types in learner_profile.py
shows up at least once in the sample output.

Run:  python3 make_sample_data.py   -> sample_data/sample_summary.csv
"""

import csv
import os
import random

SEED = 20260922
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data", "sample_summary.csv")

SUBJECTS = [
    "Participation", "Vocabulary Test", "Enrichment Test", "Enrichment HW",
    "Grammar HW", "Grammar Test", "Grammar Speaking", "Reading", "Listening",
    "Speaking", "Debate", "Science HW", "Science Test", "Science Presentation",
    "Persuasive Writing", "Persuasive Rewriting", "Compare-Contrast Writing",
    "Compare-Contrast Rewriting", "Descriptive Writing", "Descriptive Rewriting",
    "Literature HW", "Literature Test", "Novel",
]

# Which cluster each subject belongs to, for the archetype offsets below
CLUSTER_OF = {
    "Vocabulary Test": "A", "Enrichment Test": "A", "Grammar Test": "A", "Science Test": "AE",
    "Reading": "A", "Listening": "A", "Grammar HW": "AD",
    "Debate": "B", "Grammar Speaking": "B", "Speaking": "B", "Science Presentation": "BE",
    "Participation": "BD",
    "Persuasive Writing": "C", "Persuasive Rewriting": "C", "Compare-Contrast Writing": "C",
    "Compare-Contrast Rewriting": "C", "Descriptive Writing": "C", "Descriptive Rewriting": "C",
    "Novel": "C",
    "Enrichment HW": "D", "Science HW": "DE",
    "Literature HW": "D", "Literature Test": "A",
}

CUTLINES = {2: 80, 3: 70, 4: 60}
CLASS_BY_LEVEL = {
    "A": {2: "G3-21M(TeacherA)", 3: "G3-32W(TeacherC)", 4: "G3-43TU(TeacherE)"},
    "B": {2: "G3-21TH(TeacherB)", 3: "G3-32F(TeacherD)", 4: "G3-43SA(TeacherF)"},
}

# (name, level, status, tracks, base score, {cluster: offset}, rewrite delta, blank subjects)
STUDENTS = [
    ("학생일StudentA",   2, "STAY", "AB", 92, {"A": 3},            0, []),
    ("학생이StudentB",   3, "UP",   "AB", 84, {"B": 10, "A": -4},  0, []),
    ("학생삼StudentC",   3, "STAY", "AB", 76, {"C": 8},            5, []),
    ("학생사StudentD",   3, "STAY", "AB", 78, {"D": 16},           1, []),
    ("학생오StudentE",   2, "STAY", "AB", 82, {"E": 10, "A": -2},  0, []),
    ("학생육StudentF",   4, "DOWN", "AB", 58, {},                  0, ["Literature Test"]),
    ("학생칠StudentG",   4, "P",    "AB", 52, {"B": 4},            0, ["Literature Test", "Novel"]),
    ("학생팔StudentH",   3, "DOWN", "AB", 66, {"C": 3},            -2, []),
    ("학생구StudentI",   2, "STAY", "A",  88, {"B": 2},            1, []),
    ("학생십StudentJ",   4, "UP",   "A",  74, {"B": 9},            0, []),
    ("학생십일StudentK", 3, "STAY", "A",  72, {"D": 20},           0, []),
    ("학생십이StudentL", 4, "STAY", "B",  63, {},                  0, ["Literature Test"]),
    ("학생십삼StudentM", 2, "DOWN", "B",  70, {"A": 2},            0, []),
    ("학생십사StudentN", 3, "STAY", "B",  79, {"C": 6},            -3, ["Enrichment Test"]),
]


def clamp(x):
    return max(0.0, min(100.0, x))


def make_scores(rng, base, offsets, rewrite_delta, blanks):
    scores = {}
    for subj in SUBJECTS:
        if subj in blanks:
            scores[subj] = ""
            continue
        off = sum(offsets.get(c, 0) for c in CLUSTER_OF.get(subj, ""))
        val = clamp(base + off + rng.uniform(-4, 4))
        scores[subj] = round(val, 2)
    for draft, rewrite in [("Persuasive Writing", "Persuasive Rewriting"),
                           ("Compare-Contrast Writing", "Compare-Contrast Rewriting"),
                           ("Descriptive Writing", "Descriptive Rewriting")]:
        if scores.get(draft) != "" and scores.get(rewrite) != "":
            scores[rewrite] = round(clamp(scores[draft] + rewrite_delta + rng.uniform(-1, 1)), 2)
    return scores


def total_of(scores):
    academic = [v for k, v in scores.items() if v != "" and k != "Participation"]
    part = scores.get("Participation", "")
    acad_mean = sum(academic) / len(academic) if academic else 0
    if part != "":
        return round(acad_mean * 0.9 + part * 0.1, 2)
    return round(acad_mean, 2)


def main():
    rng = random.Random(SEED)
    rows = {"주2": [], "주1 Track A": [], "주1 Track B": []}
    for name, level, status, tracks, base, offsets, rw_delta, blanks in STUDENTS:
        scores = make_scores(rng, base, offsets, rw_delta, blanks)
        total = total_of(scores)
        row = {"원생명": name, "Level": level, "Status": status, **scores, "Total Average": total}
        if tracks == "AB":
            row["반명"] = f"{CLASS_BY_LEVEL['A'][level]} / {CLASS_BY_LEVEL['B'][level]}"
            row["주"] = 2
            row["Test Count"] = f"Track A: {rng.randint(6, 8)} / Track B: {rng.randint(6, 8)}"
            row["Track A Average"] = round(clamp(total + rng.uniform(-2, 2)), 2)
            row["Track B Average"] = round(clamp(total + rng.uniform(-2, 2)), 2)
            rows["주2"].append(row)
        else:
            row["반명"] = CLASS_BY_LEVEL[tracks][level]
            row["주"] = 1
            row["Test Count"] = rng.randint(6, 8)
            row["Track A Average"] = ""
            row["Track B Average"] = ""
            rows["주1 Track A" if tracks == "A" else "주1 Track B"].append(row)

    cols = ["반명", "원생명", "Level", "Status", "주", "Test Count"] + SUBJECTS + \
           ["Track A Average", "Track B Average", "Total Average"]
    empty = {c: "" for c in cols}
    cut = " / ".join(f"Lv{k}: {v}" for k, v in sorted(CUTLINES.items()))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for section, section_rows in rows.items():
            if not section_rows:
                continue
            section_rows.sort(key=lambda r: -r["Total Average"])
            w.writerow({**empty, "반명": f"=== {section} ({len(section_rows)}명) === Cutline: {cut}"})
            w.writerows(section_rows)
    print(f"Wrote {sum(len(v) for v in rows.values())} students to {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
