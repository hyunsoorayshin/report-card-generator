"""Learner classification profile — auto-comment generator.

This module is a self-contained comment engine. It classifies students into
learner types based on their scores and returns formatted comment text + table.

To create an alternative profile, copy this file, change the data/logic,
and point COMMENT_PROFILE in report_card.py at the new module.

Classification is six ordered threshold rules on cluster averages
(see ``_classify``). Nothing is fitted or trained; the learner-type labels
and the theory names attached to them are descriptive labels only.

Interface:
    get_comment(student, cutlines) → (comment_text, table_rows, type_key)
"""

# ── Level hierarchy (shared with main script) ────────────────────────────────
LEVEL_ORDER = ["2", "3", "4", "유예"]

# ── Cluster definitions ──────────────────────────────────────────────────────
# Column names are generic placeholders; rename them to match your CSV header.
# "Enrichment Test" / "Enrichment HW" stand in for an external-curriculum
# test-and-homework pair (originally a talk-based listening programme); they
# carry no special logic beyond membership in clusters A and D.
#   A = tests / structured work     B = oral / interactive
#   C = writing and reading depth   D = homework and participation
#   E = science content
CLUSTERS = {
    "A": ["Vocabulary Test", "Enrichment Test", "Grammar HW", "Grammar Test", "Science Test", "Reading", "Listening"],
    "B": ["Debate", "Grammar Speaking", "Speaking", "Science Presentation", "Participation"],
    "C": ["Persuasive Writing", "Persuasive Rewriting", "Compare-Contrast Writing", "Compare-Contrast Rewriting",
           "Descriptive Writing", "Descriptive Rewriting", "Novel"],
    "D": ["Enrichment HW", "Grammar HW", "Science HW", "Participation"],
    "E": ["Science HW", "Science Test", "Science Presentation"],
}

# ── Writing pairs for growth detection ───────────────────────────────────────
WRITING_PAIRS = [
    ("Persuasive Writing", "Persuasive Rewriting"),
    ("Compare-Contrast Writing", "Compare-Contrast Rewriting"),
    ("Descriptive Writing", "Descriptive Rewriting"),
]

# ── Growth thresholds ────────────────────────────────────────────────────────
GROWTH_THRESHOLDS = {
    "strong_grower": 3.0,
    "grower": 1.0,
    "stable": -1.0,
}

# ── Rubric intro ─────────────────────────────────────────────────────────────
RUBRIC_INTRO = (
    "본 분석은 Sternberg의 삼원지능이론, Bloom의 인지발달 단계, "
    "Gardner의 다중지능이론을 기반으로 학생의 성적 데이터를 5개 영역으로 "
    "분류하여 학습 유형을 도출한 결과입니다."
)

# ── Learner type definitions ─────────────────────────────────────────────────
LEARNER_TYPES = {
    "TYPE_1": {
        "emoji": "⭐",
        "eng": "Star Academic",
        "kor": "학업 우수형",
        "desc": (
            "시험과 정형화된 학습 과제에서 전반적으로 높은 성취를 보이는 유형입니다. "
            "문법, 어휘, 읽기 이해력이 뛰어나며, 구조화된 학습 환경에서 특히 두각을 나타냅니다. "
            "다만 창의적이거나 열린 형식의 과제에서는 때로 도전을 피하려는 경향이 있을 수 있어, "
            "앞으로는 더 높은 수준의 사고력을 요하는 활동으로 실력을 한 단계 더 발전시켜 나갈 예정입니다."
        ),
        "research": "Sternberg's Analytical Intelligence · Bloom's L3–L5 · Gardner's Linguistic-Logical",
        "table": [
            ("잘하는 점", "성장 포인트", "다음 단계"),
            ("시험 정확도가 높아요", "창의적 도전을 더 해볼 수 있어요", "심화 사고력 과제 도전"),
            ("문법·어휘가 탄탄해요", "토론에서 더 빛날 수 있어요", "열린 형식 글쓰기 경험"),
            ("숙제를 꼼꼼히 해요", "수정 과정에서 더 성장할 수 있어요", "소통형 친구와 협동 학습"),
        ],
    },
    "TYPE_2": {
        "emoji": "🗣️",
        "eng": "Communicator",
        "kor": "구두 소통형",
        "desc": (
            "말하기, 토론, 상호작용 활동에서 빛을 발하는 유형입니다. "
            "영어를 실생활에서 자신감 있게 활용하는 능력이 뛰어나며, 수업 참여도와 발표력이 특히 인상적입니다. "
            "구술 능력에 비해 필기 시험 점수가 다소 낮게 나올 수 있지만, 이는 아이의 실제 영어 실력을 온전히 "
            "반영하지 못하는 경우가 많습니다. 말하기 강점을 글쓰기로 자연스럽게 연결할 수 있도록 지도하겠습니다."
        ),
        "research": "Sternberg's Practical Intelligence · Bloom's L3–L4 · Kolb's Accommodator",
        "table": [
            ("잘하는 점", "성장 포인트", "다음 단계"),
            ("토론·말하기가 뛰어나요", "글로 표현하는 연습이 도움돼요", "말하기→글쓰기 연계 활동"),
            ("수업 참여가 적극적이에요", "문법 정리를 함께 해볼 수 있어요", "문맥 속 자연스러운 문법 학습"),
            ("실생활 영어 감각이 좋아요", "꾸준한 숙제 습관을 키워봐요", "또래 교수법으로 자신감 UP"),
        ],
    },
    "TYPE_3": {
        "emoji": "✍️",
        "eng": "Creative Writer",
        "kor": "창의적 표현형",
        "desc": (
            "글쓰기 과제에서 가장 두드러진 능력을 보이며, 초고에서 수정본으로 이어지는 과정에서 "
            "눈에 띄는 발전을 보여주는 유형입니다. 선생님의 피드백을 잘 흡수하고 스스로 표현을 다듬는 힘이 있습니다. "
            "객관식이나 시험 형식에서는 실력이 다소 저평가될 수 있지만, 글 속에 담긴 생각의 깊이와 표현력은 매우 훌륭합니다."
        ),
        "research": "Sternberg's Creative Intelligence · Bloom's L5–L6 · Gardner's Linguistic-Intrapersonal",
        "table": [
            ("잘하는 점", "성장 포인트", "다음 단계"),
            ("글쓰기 표현력이 훌륭해요", "시험에서도 실력을 보여줄 수 있어요", "수정 과정을 함께 칭찬해요"),
            ("수정할수록 더 좋아져요", "어휘 암기 연습이 도움돼요", "좋아하는 주제로 글쓰기 도전"),
            ("책 읽기에 몰입을 잘해요", "에세이 구조 연습을 해볼 수 있어요", "좋은 글 모범 사례 함께 읽기"),
        ],
    },
    "TYPE_4": {
        "emoji": "📋",
        "eng": "Diligent Worker",
        "kor": "성실 노력형",
        "desc": (
            "꾸준함과 성실함이 가장 큰 강점인 유형입니다. 숙제 완성도가 높고 어느 한 영역에서 크게 부족함 없이 "
            "균형 잡힌 모습을 보여줍니다. 점수 자체보다 노력하는 태도와 책임감이 돋보이며, 명확한 목표와 루틴 속에서 "
            "더욱 잘 성장하는 학생입니다. 앞으로는 노력에 전략적인 학습법을 더해 실력을 한층 더 끌어올릴 수 있도록 "
            "함께 도와가겠습니다."
        ),
        "research": "Dweck's Growth Mindset · Bloom's L1–L2 · Kolb's Assimilator",
        "table": [
            ("잘하는 점", "성장 포인트", "다음 단계"),
            ("숙제를 빠짐없이 해요", "전략적 학습법을 더하면 좋아요", "자기 점검 체크리스트 활용"),
            ("모든 영역이 고르게 발전해요", "시험에서 자신감을 키워봐요", "꾸준한 노력을 함께 응원해요"),
            ("칭찬에 잘 반응해요", "쉬어가며 공부하는 것도 중요해요", "심화 과제 조금씩 도전"),
        ],
    },
    "TYPE_5": {
        "emoji": "🔬",
        "eng": "Science-Logic Thinker",
        "kor": "논리·탐구형",
        "desc": (
            "과학 및 내용 중심 영어에서 특히 강한 면모를 보이는 유형입니다. "
            "과학 개념을 영어로 읽고, 이해하고, 설명하는 능력이 뛰어납니다. "
            "특히 배운 내용을 직접 설명하는 활동(Science Presentation)에서 실력이 잘 드러납니다. "
            "문학적 분석이나 설득하는 글쓰기보다는 사실 기반의 구체적인 주제에서 더 편안함을 느끼는 편이며, "
            "이런 강점을 바탕으로 다양한 글쓰기 영역으로 확장해 나갈 예정입니다."
        ),
        "research": "Sternberg's Analytical-Practical · Bloom's L3–L4 · Gardner's Logical-Naturalist",
        "table": [
            ("잘하는 점", "성장 포인트", "다음 단계"),
            ("과학 영어가 탄탄해요", "문학적 글쓰기도 도전해봐요", "과학 주제로 에세이 연습"),
            ("STEM 어휘력이 좋아요", "다양한 장르 읽기를 늘려봐요", "실생활 주제로 토론 참여"),
            ("설명하는 능력이 뛰어나요", "새로운 토론 주제에도 도전해봐요", "친구에게 가르치며 실력 UP"),
        ],
    },
    "TYPE_6": {
        "emoji": "🌱",
        "eng": "Emerging Learner",
        "kor": "성장 지원형",
        "desc": (
            "현재 여러 영역에서 학년 수준의 목표치에 도달하기 위해 노력하고 있는 단계입니다. "
            "이 유형은 고정된 평가가 아니라, 지금 이 시기에 선생님의 세심한 지원이 가장 필요한 학생임을 나타냅니다. "
            "아직 드러나지 않은 강점이 분명히 있으며, 아이의 속도와 방식에 맞는 학습 전략을 통해 꾸준한 성장을 "
            "이끌어 나가겠습니다. 가정에서의 응원과 격려가 큰 힘이 됩니다."
        ),
        "research": "Vygotsky's ZPD · Bloom's Pre-L2 · Krashen's i+1 Input Hypothesis",
        "table": [
            ("잘하는 점", "성장 포인트", "다음 단계"),
            ("수업에 참여하려는 마음이 있어요", "기초부터 차근차근 쌓아가요", "한 단계 위 과제로 도전"),
            ("숨겨진 강점이 분명히 있어요", "이해력을 함께 키워가요", "그림·문장 틀로 쉽게 접근"),
            ("응원하면 더 잘할 수 있어요", "작은 성공 경험을 쌓아가요", "성장 과정을 함께 축하해요"),
        ],
    },
}

DEFAULT_TYPE = "TYPE_4"


# ── Internal helpers ─────────────────────────────────────────────────────────

def _parse_score(val):
    if not val or val == "N/A":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _cluster_avg(scores, keys):
    vals = [v for k in keys if (v := _parse_score(scores.get(k, ""))) is not None]
    return sum(vals) / len(vals) if vals else None


def _compute_level_avg(level, section, cutlines):
    current = cutlines.get((section, level))
    if current is None:
        return 64
    try:
        idx = LEVEL_ORDER.index(level)
    except ValueError:
        return current
    if idx > 0:
        higher = cutlines.get((section, LEVEL_ORDER[idx - 1]))
        if higher is not None:
            return (current + higher) / 2
    return current


def _compute_growth_flag(scores):
    deltas = []
    for draft, rewrite in WRITING_PAIRS:
        d = _parse_score(scores.get(draft, ""))
        r = _parse_score(scores.get(rewrite, ""))
        if d is not None and r is not None:
            deltas.append(r - d)
    if not deltas:
        return "N/A"
    avg = sum(deltas) / len(deltas)
    if avg >= GROWTH_THRESHOLDS["strong_grower"]:
        return "STRONG_GROWER"
    if avg >= GROWTH_THRESHOLDS["grower"]:
        return "GROWER"
    if avg >= GROWTH_THRESHOLDS["stable"]:
        return "STABLE"
    return "REGRESSOR"


# ── Classification logic ─────────────────────────────────────────────────────

def _classify(scores, total_str, result, level, section, cutlines):
    """Classify a student into one of 6 learner types. Returns type key."""
    total = _parse_score(total_str)
    cluster_vals = {k: _cluster_avg(scores, v) for k, v in CLUSTERS.items()}
    A, B, C, D, E = (cluster_vals.get(k) for k in "ABCDE")
    growth = _compute_growth_flag(scores)
    level_avg = _compute_level_avg(level, section, cutlines)

    # Step 1: Star Academic — high total, strong tests, decent oral or writing
    if total and A and total >= 80 and A >= 85 \
            and ((B and B >= 75) or (C and C >= 75)):
        return "TYPE_1"

    # Step 2: Communicator — speaking dominant over tests
    if B and A and B >= 75 and B >= (A or 0) and B >= (C or 0) \
            and (B - (A or 0)) >= 5:
        return "TYPE_2"

    # Step 3: Science-Logic Thinker — strong science cluster
    sci_test = _parse_score(scores.get("Science Test", ""))
    if E and E >= 80 and sci_test and sci_test >= 75:
        return "TYPE_5"

    # Step 4: Creative Writer — writing dominant with growth
    if C and C >= 72 and growth in ("GROWER", "STRONG_GROWER") \
            and C >= (B or 0) and C >= (A or 0):
        return "TYPE_3"

    # Step 5: Diligent Worker — high homework, no weak clusters
    if D and D >= 90:
        if all(v is None or v >= 60 for v in cluster_vals.values()):
            return "TYPE_4"

    # Step 6: Emerging Learner — needs support
    below_count = sum(1 for v in cluster_vals.values()
                      if v is not None and v < 65)
    if result == "DOWN":
        return "TYPE_6"
    if total and total < (level_avg - 8):
        return "TYPE_6"
    if below_count >= 3:
        return "TYPE_6"

    return DEFAULT_TYPE


# ── Public interface ─────────────────────────────────────────────────────────

def get_comment(student, cutlines):
    """Classify a student and return a list of content blocks.

    Each block is a dict with a "type" key:
      {"type": "text",  "value": "...", "style": "normal"}   — normal paragraph
      {"type": "text",  "value": "...", "style": "heading"}  — bold heading line
      {"type": "text",  "value": "...", "style": "small"}    — small/light text
      {"type": "table", "rows": [("col1","col2","col3"), ...]} — table with header row first

    The report card script renders these generically — it knows nothing
    about learner types, research citations, or classification logic.
    """
    ltype = _classify(
        student["scores"], student["total"], student["result"],
        student["current_level"], student["section"], cutlines,
    )
    t = LEARNER_TYPES[ltype]

    blocks = [
        {"type": "text", "value": f"{t['emoji']}  {t['eng']} · {t['kor']}", "style": "heading"},
        {"type": "text", "value": t["desc"], "style": "normal"},
        {"type": "table", "rows": list(t["table"])},
        {"type": "text", "value": RUBRIC_INTRO, "style": "small"},
        {"type": "text", "value": f"({t['research']})", "style": "small"},
    ]
    return blocks
