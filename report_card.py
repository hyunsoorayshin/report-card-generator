#!/usr/bin/env python3
"""Report Card Generator — generates individual PNG report cards for each student."""

import csv
import os
import platform
import re
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                         SETTINGS — CHANGE HERE                          ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# ── Folders (defaults; override with --csv-dir / --out-dir) ─────────────────
CSV_DIR = os.path.join(BASE_DIR, "sample_data")     # where summary CSVs are read from
OUTPUT_DIR = os.path.join(BASE_DIR, "output")       # where PNGs are saved
QR_PATH = os.path.join(BASE_DIR, "qr.png")          # optional: pasted top-right only if the file exists

# ── CSV column names ─────────────────────────────────────────────────────────
# Must match the header row in your CSV files.
COL_CLASS = "반명"
COL_NAME = "원생명"
COL_LEVEL = "Level"
COL_STATUS = "Status"
COL_TOTAL = "Total Average"
SCORE_START_COL = 6          # subject score columns start at this index

# ── Auto comment ─────────────────────────────────────────────────────────────
# True  → auto-generate comments using COMMENT_PROFILE below
# False → only use COMMENT_OVERRIDES (manual per-student comments)
AUTO_COMMENT = True

# Which comment generator module to use (must have a get_comment function).
# Swap this to use a different classification/comment system.
#   e.g. "learner_profile", "learner_profile_v2", "my_custom_comments"
COMMENT_PROFILE = "learner_profile"

# Manual overrides — always takes priority over auto comments.
# Key = student name exactly as it appears in CSV.
#
# Write them by hand, or have any assistant draft them in this exact format
# (one entry per line, key = "<Korean name><EnglishName>" as in the CSV).
# The two entries below are placeholders that match the synthetic sample data.
COMMENT_OVERRIDES = {
    "학생일StudentA": "이번 달에도 꾸준히 노력한 모습이 보였습니다. (placeholder comment)",
    "학생이StudentB": "토론 시간에 적극적으로 참여해 주었어요. (placeholder comment)",
    }

# ── Radar chart ──────────────────────────────────────────────────────────────
# Each entry: (label on chart, [CSV column names to average for that axis])
# Add/remove entries to change the number of radar points.
RADAR_CATEGORIES = [
    ("Vocab",     ["Vocabulary Test", "Grammar Test"]),
    ("Speaking",  ["Debate", "Science Presentation"]),
    ("Writing",   ["Persuasive Writing", "Persuasive Rewriting", "Compare-Contrast Writing",
                   "Descriptive Writing", "Descriptive Rewriting"]),
    ("Listening", ["Listening"]),
    ("Reading",   ["Reading", "Novel", "Literature Test"]),
    ("Science",   ["Science HW", "Science Test", "Science Presentation"]),
    ("Homework",  ["Literature HW", "Science HW"]),
]

RADAR_MAX_SCALE = 5          # max points on the radar chart

# Score-to-scale bands: (min_score, max_score, scale_value)
# Evaluated top-down, first match wins.
RADAR_SCALE_BANDS = [
    (100, 100,    5),
    (90,  99.99,  4),
    (70,  89.99,  3),
    (60,  69.99,  2),
    (50,  59.99,  1),
    (0,   49.99,  0),
]

# ── Image quality ────────────────────────────────────────────────────────────
SCALE = 3                    # resolution multiplier (higher = crisper PNG)

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                    END OF SETTINGS — code below                          ║
# ╚════════════════════════════════════════════════════════════════════════════╝


def score_to_scale(score):
    """Convert a percentage score to the radar scale."""
    for lo, hi, val in RADAR_SCALE_BANDS:
        if lo <= score <= hi:
            return val
    return 0


def _parse_score(val):
    """Parse a score string to float, or None if N/A/empty."""
    if not val or val == "N/A":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def get_comment_blocks(student, cutlines):
    """Return a list of content blocks for the comment box, or None.

    Each block is a dict: {"type": "text", "value": ..., "style": ...}
                      or: {"type": "table", "rows": [...]}

    COMMENT_OVERRIDES always takes priority (rendered as a single text block).
    When AUTO_COMMENT is True, delegates to the COMMENT_PROFILE module.
    """
    if student["name"] in COMMENT_OVERRIDES:
        return [{"type": "text", "value": COMMENT_OVERRIDES[student["name"]], "style": "normal"}]

    if not AUTO_COMMENT:
        return None

    import importlib
    profile = importlib.import_module(COMMENT_PROFILE)
    return profile.get_comment(student, cutlines)

# Fonts — auto-detect OS
if platform.system() == "Windows":
    FONT_KR = "C:/Windows/Fonts/malgun.ttf"       # Malgun Gothic (Korean)
    FONT_KR_BOLD = "C:/Windows/Fonts/malgunbd.ttf" # Malgun Gothic Bold
    FONT_EN = "C:/Windows/Fonts/arial.ttf"
else:  # macOS
    FONT_KR = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    FONT_KR_BOLD = None  # uses index=5 on macOS
    FONT_EN = "/System/Library/Fonts/Helvetica.ttc"


def load_fonts():
    """Load fonts with fallbacks."""
    S = SCALE
    try:
        title = ImageFont.truetype(FONT_KR, 30 * S)
        heading = ImageFont.truetype(FONT_KR, 20 * S)
        body = ImageFont.truetype(FONT_KR, 16 * S)
        if FONT_KR_BOLD:
            body_bold = ImageFont.truetype(FONT_KR_BOLD, 16 * S)
        else:
            body_bold = ImageFont.truetype(FONT_KR, 16 * S, index=5)
        small = ImageFont.truetype(FONT_KR, 10 * S)
        small_plus = ImageFont.truetype(FONT_KR, 11 * S)
        xsmall = ImageFont.truetype(FONT_KR, 9 * S)
        score = ImageFont.truetype(FONT_KR, 18 * S)
        total = ImageFont.truetype(FONT_EN, 20 * S)
        radar_label = ImageFont.truetype(FONT_EN, 11 * S)
    except Exception:
        default = ImageFont.load_default()
        title = heading = body = body_bold = small = small_plus = xsmall = score = total = radar_label = default
    return {
        "title": title,
        "heading": heading,
        "body": body,
        "body_bold": body_bold,
        "small": small,
        "small_plus": small_plus,
        "xsmall": xsmall,
        "score": score,
        "total": total,
        "radar_label": radar_label,
    }


# ── CSV Parsing ──────────────────────────────────────────────────────────────

# Level hierarchy: lower number = more advanced
LEVEL_ORDER = ["2", "3", "4", "유예"]


def _derive_final_level(current_level, status):
    """Derive final level from current level and status.

    Students move one level at a time:
      UP   → level - 1 (e.g., Lv3 → Lv2)
      STAY → same level
      DOWN → level + 1 (e.g., Lv3 → Lv4)
      P    → 유예 (probation)
    """
    status = status.strip().upper()
    if status == "P":
        return "유예"
    # Probation students who go UP return to Level 4
    if current_level.strip().upper() == "P" and status == "UP":
        return "4"
    try:
        lv = int(current_level)
    except (ValueError, TypeError):
        return current_level  # can't parse, return as-is
    if status == "UP":
        return str(max(lv - 1, 2))  # can't go above Lv2
    elif status == "DOWN":
        return str(lv + 1)
    else:  # STAY or anything else
        return str(lv)


def _parse_cutlines(text):
    """Extract cutlines like 'Lv2: 80 / Lv3: 70 / Lv4: 60' from a header string.

    Returns dict: {"2": 80.0, "3": 70.0, "4": 60.0, "유예": <same as L4>}
    """
    cutlines = {}
    for m in re.finditer(r"(?:Level\s*|Lv?)(\d):\s*([\d.]+)", text):
        level = m.group(1)
        value = round(float(m.group(2)), 2)
        cutlines[level] = value
    # 유예 students use L4 cutline
    if "4" in cutlines:
        cutlines["유예"] = cutlines["4"]
    return cutlines


def parse_csv(csv_path):
    """Parse a grade CSV and return (students, cutlines).

    Reads the header row to auto-detect column positions, then parses
    section headers (=== ... ===) for cutlines and student data rows.
    """
    students = []
    cutlines = {}
    current_section = None
    header_map = {}  # column name → index
    score_cols = []  # auto-detected subject column names
    student_num = 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            cell0 = row[0].strip()

            # First row with the expected column name is the header
            if not header_map and cell0 == COL_CLASS:
                header_map = {col.strip(): i for i, col in enumerate(row)}
                score_cols = [
                    col.strip() for i, col in enumerate(row)
                    if i >= SCORE_START_COL and col.strip()
                    and not col.strip().endswith("Average")
                ]
                continue

            # Detect section headers: === 주2 (139명) === Cutline: ...
            if cell0.startswith("==="):
                sec_match = re.match(r"===\s*(.+?)\s*\(", cell0)
                current_section = sec_match.group(1).strip() if sec_match else cell0
                for lv, val in _parse_cutlines(cell0).items():
                    cutlines[(current_section, lv)] = val
                continue

            # Skip rows before header or section is detected
            if not header_map or current_section is None:
                continue

            # Skip rows without a valid student name
            name_idx = header_map.get(COL_NAME)
            if name_idx is None or name_idx >= len(row) or not row[name_idx].strip():
                continue

            # Skip non-data rows (empty class column, etc.)
            if not cell0:
                continue

            # Parse class/teacher info: "G5-34W(Alex) / G5-34SA(Ray)"
            classes = [
                (m.group(1), m.group(2))  # (class_name, teacher)
                for m in re.finditer(r"([\w-]+)\((\w+)\)", cell0)
            ]

            student_num += 1

            # Build scores dict from auto-detected subject columns
            scores = {}
            for col_name in score_cols:
                col_idx = header_map.get(col_name)
                if col_idx is not None and col_idx < len(row):
                    scores[col_name] = row[col_idx].strip()
                else:
                    scores[col_name] = ""

            level_idx = header_map.get(COL_LEVEL)
            status_idx = header_map.get(COL_STATUS)
            total_idx = header_map.get(COL_TOTAL)

            current_level = row[level_idx].strip() if level_idx is not None and level_idx < len(row) else ""
            status = row[status_idx].strip() if status_idx is not None and status_idx < len(row) else ""
            total = row[total_idx].strip() if total_idx is not None and total_idx < len(row) else ""

            students.append({
                "number": student_num,
                "name": row[name_idx].strip(),
                "current_level": current_level,
                "result": status,
                "final_level": _derive_final_level(current_level, status),
                "scores": scores,
                "total": total,
                "section": current_section,
                "classes": classes,
            })

    return students, cutlines


# ── Report Card Generation ───────────────────────────────────────────────────

# Layout constants (all scaled by SCALE)
S = SCALE
WIDTH = 820 * S
MARGIN = 40 * S
BOX_COLS = 5        # boxes per row
BOX_W = 140 * S     # box width
BOX_H = 65 * S      # box height
BOX_GAP = 6 * S     # gap between boxes
COLORS = {
    "bg": "#FFFFFF",
    "primary": "#1a2332",
    "accent": "#2563eb",
    "light_bg": "#f1f5f9",
    "text": "#1e293b",
    "text_gray": "#64748b",
    "border": "#cbd5e1",
    "highlight": "#dbeafe",
    "white": "#FFFFFF",
    "up": "#16a34a",
    "down": "#dc2626",
    "stay": "#2563eb",
}


def split_name(name):
    """Split a mixed name like '박서준2Jayden' into (korean, english).

    Digits before the first English letter stay with the Korean part
    (they indicate duplicate names).
    """
    first_eng = None
    for i, c in enumerate(name):
        if c.isascii() and c.isalpha():
            first_eng = i
            break
    if first_eng is None:
        return name.strip(), ""
    return name[:first_eng].strip(), name[first_eng:].strip()


def result_color(result):
    if result == "UP":
        return COLORS["up"]
    if result == "DOWN":
        return COLORS["down"]
    return COLORS["stay"]


def result_color_banner(result):
    """Lighter result colors for dark banner background."""
    if result == "UP":
        return "#4ade80"
    if result == "DOWN":
        return "#f87171"
    return "#93c5fd"


def compute_radar_values(scores):
    """Compute radar chart values from a student's scores dict.

    Returns list of (label, scale_value) for each RADAR_CATEGORIES entry.
    """
    results = []
    for label, subjects in RADAR_CATEGORIES:
        vals = []
        for subj in subjects:
            raw = scores.get(subj, "")
            if raw and raw != "N/A":
                try:
                    vals.append(float(raw))
                except ValueError:
                    pass
        if vals:
            avg = sum(vals) / len(vals)
            results.append((label, score_to_scale(avg)))
        else:
            results.append((label, 0))
    return results


def draw_radar(img, cx, cy, radius, values, fonts, colors):
    """Draw a circular radar chart with transparent fill on img.

    values: list of (label, scale_value) — one per axis.
    """
    import math

    S = SCALE
    n = len(values)
    max_s = RADAR_MAX_SCALE
    angle_step = 2 * math.pi / n
    start_angle = -math.pi / 2  # start from top

    draw = ImageDraw.Draw(img)

    def point(axis_idx, scale):
        angle = start_angle + axis_idx * angle_step
        r = radius * scale / max_s
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    # Draw concentric circle rings
    for s in range(1, max_s + 1):
        r = radius * s / max_s
        bbox = [(cx - r, cy - r), (cx + r, cy + r)]
        draw.ellipse(bbox, outline="#e2e8f0", width=S)

    # Draw axis lines
    for i in range(n):
        ox, oy = point(i, max_s)
        draw.line([(cx, cy), (ox, oy)], fill="#e2e8f0", width=S)

    # Draw data polygon with transparent fill using RGBA overlay
    data_pts = [point(i, val) for i, (_, val) in enumerate(values)]
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.polygon(data_pts, fill=(37, 99, 235, 50))
    overlay_draw.polygon(data_pts, outline=(37, 99, 235, 200), width=2 * S)
    img.paste(Image.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 0)), overlay), mask=overlay)

    # Redraw on main draw after compositing
    draw = ImageDraw.Draw(img)

    # Dots at each data point
    for px, py in data_pts:
        dot_r = 4 * S
        draw.ellipse(
            [(px - dot_r, py - dot_r), (px + dot_r, py + dot_r)],
            fill="#2563eb", outline="#1d4ed8", width=S,
        )

    # Labels outside the chart
    label_margin = 20 * S
    for i, (label, val) in enumerate(values):
        angle = start_angle + i * angle_step
        lx = cx + (radius + label_margin) * math.cos(angle)
        ly = cy + (radius + label_margin) * math.sin(angle)
        draw.text((lx, ly), label, fill=colors["text_gray"], font=fonts["radar_label"], anchor="mm")


def generate_report_card(student, fonts, cutlines):
    """Generate a PNG report card image for one student."""
    import math

    all_scores = [(k, v) for k, v in student["scores"].items() if v and v != "N/A"]

    korean_name, english_name = split_name(student["name"])
    display_name = korean_name + " " + english_name if english_name else korean_name

    # Fit BOX_COLS boxes per row, derive box width from available space
    cols = BOX_COLS
    avail_w = WIDTH - MARGIN * 2
    box_w = (avail_w - (cols - 1) * BOX_GAP) // cols

    S = SCALE

    # Start with an oversized canvas — will be cropped to actual content height
    bottom_h = 250 * S
    comment_blocks = get_comment_blocks(student, cutlines)
    max_height = 3000 * S  # generous upper bound

    img = Image.new("RGB", (WIDTH, max_height), COLORS["bg"])
    C = COLORS

    # ── Diagonal prism banner (covers title + student info) ──
    banner_h = 140 * S
    band_colors = [
        (16, 28, 50),    # deep navy
        (22, 38, 65),    # dark blue
        (30, 52, 85),    # medium blue
        (20, 44, 75),    # blue
        (14, 24, 45),    # deep navy
    ]
    band_w = WIDTH // len(band_colors) + 80 * S
    skew = 40 * S
    for i, col in enumerate(band_colors):
        x0 = i * (band_w - 40 * S) - 40 * S
        pts = [
            (x0 + skew, 0),
            (x0 + band_w + skew, 0),
            (x0 + band_w - skew, banner_h),
            (x0 - skew, banner_h),
        ]
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).polygon(pts, fill=col + (180,))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── Row 1: Name (centered on the full width) + optional QR (right) ──
    row1_y = 20 * S
    row1_center = row1_y + 25 * S  # vertical center of row 1

    # Student name (anchor "mm" centers it on the canvas regardless of what sits at the edges)
    draw.text((WIDTH // 2, row1_center), display_name, fill="#FFFFFF", font=fonts["title"], anchor="mm")

    # Optional QR code (right, vertically centered with name). Supply your own QR_PATH file;
    # nothing is drawn when the file is absent.
    if os.path.exists(QR_PATH):
        qr = Image.open(QR_PATH).convert("RGBA")
        qr_h = int(40 * S)
        qr_w = qr_h
        qr = qr.resize((qr_w, qr_h), Image.LANCZOS)
        qr_x = WIDTH - MARGIN - qr_w
        qr_y = row1_center - qr_h // 2
        img_rgba = img.convert("RGBA")
        img_rgba.paste(qr, (qr_x, qr_y), mask=qr)
        img = img_rgba.convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── Row 2: Thin accent separator ──
    y = row1_y + 55 * S
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill="#4a8fe7", width=S)
    y += 12 * S

    # ── Row 3: Level transition + result ──
    section = student["section"]
    col_mid = WIDTH // 2
    col_right = WIDTH - MARGIN

    level_text = f"Lv {student['current_level']}  →  Lv {student['final_level']}"
    draw.text((col_mid, y), level_text, fill="#FFFFFF", font=fonts["body_bold"], anchor="mt")
    res = student["result"]
    draw.text((col_right, y), res, fill=result_color_banner(res), font=fonts["body_bold"], anchor="rt")
    y += 20 * S

    # ── Row 4: Cutlines for all levels ──
    cutline_parts = []
    for lv in ["2", "3", "4"]:
        cl = cutlines.get((section, lv))
        if cl is not None:
            cutline_parts.append(f"Lv{lv}: {cl}")
    cutline_text = "Cutline   " + "   /   ".join(cutline_parts) if cutline_parts else ""
    draw.text((col_mid, y), cutline_text, fill="#8badc9", font=fonts["small"], anchor="mt")

    y = banner_h + 12 * S

    # ── Score boxes ──
    grid_w = cols * box_w + (cols - 1) * BOX_GAP
    grid_left = (WIDTH - grid_w) // 2  # center the grid

    for i, (cat, val) in enumerate(all_scores):
        c = i % cols
        r = i // cols
        bx = grid_left + c * (box_w + BOX_GAP)
        by = y + r * (BOX_H + BOX_GAP)
        cx = bx + box_w // 2  # center x of box

        # Box background
        draw.rectangle([(bx, by), (bx + box_w, by + BOX_H)], fill=C["light_bg"], outline=C["border"], width=S)
        # Subject label (top, centered)
        draw.text((cx, by + 6 * S), cat, fill=C["text_gray"], font=fonts["small_plus"], anchor="mt")
        # Score (center, bigger) — show N/A in gray
        try:
            display_val = f"{float(val):.2f}"
        except (ValueError, TypeError):
            display_val = val if val else "N/A"
        val_color = C["text_gray"] if display_val == "N/A" else C["primary"]
        draw.text((cx, by + 34 * S), display_val, fill=val_color, font=fonts["score"], anchor="mm")

    box_rows = math.ceil(len(all_scores) / cols)
    y += box_rows * (BOX_H + BOX_GAP) + 8 * S
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=C["border"], width=S)
    y += 12 * S

    # ── Bottom section: Total box (left 1/3) + Radar chart (right 2/3) ──
    third_w = (WIDTH - MARGIN * 2) // 3

    # Total box (vertically centered in bottom area)
    total_box_h = BOX_H + 30 * S
    total_w = third_w
    tx = grid_left
    tcx = tx + total_w // 2
    total_box_y = y + (bottom_h - total_box_h) // 2
    draw.rectangle([(tx, total_box_y), (tx + total_w, total_box_y + total_box_h)],
                   fill=C["highlight"], outline=C["accent"], width=2 * S)
    draw.text((tcx, total_box_y + 12 * S), "Total", fill=C["text_gray"], font=fonts["body"], anchor="mt")
    try:
        total_display = f"{float(student['total']):.2f}"
    except (ValueError, TypeError):
        total_display = student["total"]
    draw.text((tcx, total_box_y + total_box_h // 2 + 10 * S), total_display,
              fill=C["primary"], font=fonts["title"], anchor="mm")

    # Radar chart (right 2/3, can use full bottom height)
    radar_values = compute_radar_values(student["scores"])
    radar_area_left = tx + total_w + BOX_GAP * 2
    radar_area_right = grid_left + grid_w
    radar_cx = (radar_area_left + radar_area_right) // 2
    radar_cy = y + bottom_h // 2
    radar_radius = min(bottom_h // 2 - 30 * S, (radar_area_right - radar_area_left) // 2 - 35 * S)
    draw_radar(img, radar_cx, radar_cy, radar_radius, radar_values, fonts, C)

    y += bottom_h + 8 * S
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=C["border"], width=S)
    y += 10 * S

    # ── Teacher comment ──
    if comment_blocks:
        draw.text((MARGIN, y), "Teacher's Comment", fill=C["primary"], font=fonts["body_bold"])
        y += 24 * S
        max_w = WIDTH - MARGIN * 2

        for block in comment_blocks:
            if block["type"] == "text":
                style = block.get("style", "normal")
                if style == "heading":
                    font_use, color_use, line_h = fonts["body_bold"], C["primary"], 22 * S
                elif style == "small":
                    font_use, color_use, line_h = fonts["xsmall"], "#94a3b8", 13 * S
                else:
                    font_use, color_use, line_h = fonts["body"], C["text"], 20 * S
                center = style == "small"
                for paragraph in block["value"].split("\n"):
                    words = paragraph.split()
                    lines, cur = [], ""
                    for w in words:
                        test = f"{cur} {w}".strip()
                        if draw.textlength(test, font=font_use) <= max_w:
                            cur = test
                        else:
                            if cur:
                                lines.append(cur)
                            cur = w
                    if cur:
                        lines.append(cur)
                    for line in lines:
                        if center:
                            draw.text((WIDTH // 2, y), line, fill=color_use, font=font_use, anchor="mt")
                        else:
                            draw.text((MARGIN, y), line, fill=color_use, font=font_use)
                        y += line_h
                    y += 4 * S

            elif block["type"] == "table":
                rows = block["rows"]
                num_cols = len(rows[0]) if rows else 0
                table_w = WIDTH - MARGIN * 2
                col_w = table_w // max(num_cols, 1)
                row_h = 22 * S
                for ri, row_data in enumerate(rows):
                    for ci, cell in enumerate(row_data):
                        cx = MARGIN + ci * col_w
                        if ri == 0:
                            draw.rectangle([(cx, y), (cx + col_w, y + row_h)],
                                           fill=C["accent"], outline=C["border"], width=S)
                            draw.text((cx + col_w // 2, y + row_h // 2), cell,
                                      fill="#FFFFFF", font=fonts["small"], anchor="mm")
                        else:
                            draw.rectangle([(cx, y), (cx + col_w, y + row_h)],
                                           fill=C["light_bg"] if ri % 2 == 0 else C["bg"],
                                           outline=C["border"], width=S)
                            draw.text((cx + col_w // 2, y + row_h // 2), cell,
                                      fill=C["text"], font=fonts["small"], anchor="mm")
                    y += row_h
                y += 8 * S

        y += 8 * S
        draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=C["border"], width=S)
        y += 10 * S

    y += 20 * S  # bottom padding below the last separator line

    # Crop canvas to actual content height
    img = img.crop((0, 0, WIDTH, y))

    return img


def english_name(name):
    """Extract the English portion of a mixed Korean/English name."""
    chars = [c for c in name if ord(c) < 128 and c.isalpha()]
    return "".join(chars) if chars else "noname"


# ── Main ─────────────────────────────────────────────────────────────────────


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Render one PNG report card per student from summary CSVs.")
    parser.add_argument("--csv-dir", default=CSV_DIR, help=f"folder of summary CSVs (default: {os.path.relpath(CSV_DIR, BASE_DIR)}/)")
    parser.add_argument("--out-dir", default=OUTPUT_DIR, help=f"where PNGs are written (default: {os.path.relpath(OUTPUT_DIR, BASE_DIR)}/)")
    parser.add_argument("--teacher", default=None,
                        help="teacher tag to generate for, or 'all' (omit to be prompted)")
    args = parser.parse_args(argv)
    csv_dir, out_dir = args.csv_dir, args.out_dir

    if not os.path.isdir(csv_dir):
        raise FileNotFoundError(f"CSV folder not found at: {csv_dir}")
    csv_files = sorted([
        os.path.join(csv_dir, f) for f in os.listdir(csv_dir)
        if f.lower().endswith(".csv")
    ])
    if not csv_files:
        raise FileNotFoundError(f"No .csv files in: {csv_dir}")

    # Collect all teachers across all CSVs first
    all_teachers = set()
    all_csv_data = []
    for csv_path in csv_files:
        students, cutlines = parse_csv(csv_path)
        all_csv_data.append((csv_path, students, cutlines))
        for s in students:
            for _, teacher in s["classes"]:
                all_teachers.add(teacher)

    # Which teacher to generate for: --teacher, or ask interactively
    sorted_teachers = sorted(all_teachers)
    print(f"\nTeachers found: {', '.join(sorted_teachers)}")
    if args.teacher is not None:
        choice = args.teacher.strip()
    else:
        choice = input("Generate for which teacher? (all / teacher name): ").strip()
    if choice.lower() == "all":
        selected_teachers = None  # generate for all
    else:
        selected_teachers = {choice}

    fonts = load_fonts()
    total_saved = 0
    # Track DOWN students per teacher
    down_students = {}  # teacher → list of student info dicts

    for csv_path, students, cutlines in all_csv_data:
        csv_name = os.path.basename(csv_path)
        print(f"\n{'='*60}")
        print(f"Processing: {csv_name}")
        print(f"{'='*60}")
        print(f"Found {len(students)} students")

        for s in students:
            # Check if any of this student's classes match the selected teacher
            matching_classes = [
                (cn, t) for cn, t in s["classes"]
                if selected_teachers is None or t in selected_teachers
            ]
            if not matching_classes:
                continue

            img = generate_report_card(s, fonts, cutlines)
            kor, eng = split_name(s["name"])
            filename = f"{kor} {eng} Report Card.png"
            for class_name, teacher in matching_classes:
                class_dir = os.path.join(out_dir, teacher, class_name)
                os.makedirs(class_dir, exist_ok=True)
                img.save(os.path.join(class_dir, filename))
                print(f"  {teacher}/{class_name}/{filename}")
                total_saved += 1

                # Collect DOWN students
                if s["result"] == "DOWN":
                    down_students.setdefault(teacher, []).append({
                        "name": s["name"],
                        "class": class_name,
                        "current_level": s["current_level"],
                        "final_level": s["final_level"],
                        "total": s["total"],
                    })

    # Generate DOWN student list per teacher
    for teacher, down_list in down_students.items():
        teacher_dir = os.path.join(out_dir, teacher)
        os.makedirs(teacher_dir, exist_ok=True)
        filepath = os.path.join(teacher_dir, "level_down_students.csv")
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Class", "Current Level", "Final Level", "Total"])
            for d in down_list:
                writer.writerow([d["name"], d["class"], d["current_level"], d["final_level"], d["total"]])
        print(f"\nDOWN student list saved: {filepath} ({len(down_list)} students)")

    print(f"\nDone — {total_saved} report cards saved to: {out_dir}")


if __name__ == "__main__":
    main()
