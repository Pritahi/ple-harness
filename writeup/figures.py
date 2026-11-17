"""Writeup figures for the PLE agent harness submission."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = "/tmp/writeup-wt/writeup"

# ---------- Figure 1: architecture ----------
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.axis("off")

def box(x, y, w, h, text, fc="#eef3fb", ec="#33507a", fs=9, bold_first=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                fc=fc, ec=ec, lw=1.4))
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.055 - i * 0.052, ln, ha="center",
                va="top", fontsize=fs,
                fontweight="bold" if i == 0 and bold_first else "normal")

def arrow(x1, y1, x2, y2, label="", rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                 connectionstyle=f"arc3,rad={rad}",
                                 arrowstyle="-|>", mutation_scale=14,
                                 color="#33507a", lw=1.4))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.035, label, ha="center",
                fontsize=7.5, style="italic", color="#33507a")

box(0.03, 0.62, 0.20, 0.30, "PLANNER (10%)\nread-only tools\nextracts DELIVERABLES:\nfallback: parse task text")
box(0.30, 0.62, 0.26, 0.30, "WORKER (75%)\nbash / read / write / edit + MCP\nescalating deliverable nudge (66%)\nforce-write gate (last 30%)")
box(0.63, 0.62, 0.16, 0.30, "VERIFIER (15%)\nexecutes the\ndeliverable,\nrubric checklist")
box(0.83, 0.62, 0.14, 0.30, "FIX ROUNDS\nverdict ->\nworker\n(x2 max)")
box(0.15, 0.14, 0.32, 0.30, "BUDGET LAYER\nTPM pacer (15k/min, 16k ceiling)\ncompaction at 4k tokens\ncontext-full halving\nshort-task bypass (<45 min)")
box(0.55, 0.14, 0.32, 0.30, "ENFORCEMENT LAYER\nfinish refused without deliverable\nformat check: magic bytes\ncontent check: >=100 words (docx)\ndisk re-verify after every bash")

arrow(0.23, 0.77, 0.30, 0.77, "plan")
arrow(0.56, 0.77, 0.63, 0.77, "summary")
arrow(0.79, 0.77, 0.83, 0.77, "verdict")
arrow(0.87, 0.62, 0.45, 0.50, "", rad=0.25)
ax.text(0.68, 0.52, "findings", fontsize=7.5, style="italic", color="#33507a", ha="center")
arrow(0.31, 0.44, 0.38, 0.62, "", rad=-0.2)
arrow(0.66, 0.44, 0.52, 0.62, "", rad=0.2)

ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("Figure 1 - Harness architecture: role split with time shares and the two cross-cutting layers",
             fontsize=10, pad=10)
fig.savefig(f"{OUT}/fig1_architecture.png", dpi=170, bbox_inches="tight")
plt.close(fig)

# ---------- Figure 2: failure taxonomy ----------
layers = [
    ("quota death", "429s killed runs; TPM pacer + compaction"),
    ("no deliverable", "5h exploring, zero writes; escalating nudge"),
    ("scratch loophole", "any write fed the nudge; deliverable-aware"),
    ("stub plan", "DELIVERABLES line lost; task-text fallback"),
    ("early quit", "gave up; finish refusal (2x)"),
    ("fix-loop", "ignored nudges; force-write gate"),
    ("invalid format", "text in .docx; magic-byte check"),
    ("hollow container", "4-word valid docx; word floor"),
    ("gate catch-22", "builder blocked; produce-only blocking"),
    ("explore-forever", "92 ignored nudges; harness salvage"),
]
fig, ax = plt.subplots(figsize=(9, 4.6))
ys = range(len(layers), 0, -1)
for (name, fix), y in zip(layers, ys):
    ax.barh(y, 1, left=0, height=0.62, color="#c33", alpha=0.85)
    ax.barh(y, 1, left=1.02, height=0.62, color="#2c7a3f", alpha=0.85)
    ax.text(-0.03, y, name, ha="right", va="center", fontsize=9, fontweight="bold")
    ax.text(0.5, y, "fails", ha="center", va="center", fontsize=7.5, color="white")
    ax.text(1.54, y, "fixed", ha="center", va="center", fontsize=7.5, color="white")
    ax.text(2.12, y, fix, ha="left", va="center", fontsize=8)
ax.text(0.5, len(layers) + 0.8, "failure layer", ha="center", fontsize=9, fontweight="bold", color="#c33")
ax.text(1.54, len(layers) + 0.8, "harness response", ha="center", fontsize=9, fontweight="bold", color="#2c7a3f")
ax.set_xlim(-0.85, 3.6); ax.set_ylim(0.3, len(layers) + 1.3)
ax.axis("off")
ax.set_title("Figure 2 - Ten failure layers found by dev runs; each visible only after the previous fix",
             fontsize=10, pad=8)
fig.savefig(f"{OUT}/fig2_taxonomy.png", dpi=170, bbox_inches="tight")
plt.close(fig)

# ---------- Figure 3: run outcomes ----------
runs = ["run7", "run8", "run9", "run14", "run15", "run16", "run17", "run18",
        "run19", "run20", "run21", "run22", "run23", "run24", "run25", "run26",
        "run27", "run28", "run29*", "run31*", "run32*", "run33*"]
scores = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0435, 0.1774, 0, 0, 0.0435, 0, 0,
          0, 0.0435, 0, 0.1935, 0, 0.0817]
colors = []
for r, s in zip(runs, scores):
    colors.append(("#2c7a3f" if s > 0 else "#c33") if r.endswith("*") else
                  ("#7fbf8f" if s > 0 else "#e0a3a3"))
fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.bar(range(len(runs)), scores, color=colors)
ax.set_xticks(range(len(runs)))
ax.set_xticklabels([r.replace("*", "\n*") for r in runs], fontsize=7.5)
ax.axhline(0.138, color="#33507a", ls="--", lw=1.2)
ax.text(0.2, 0.145, "Stage-2 eligibility line (mean >= 0.138)", fontsize=8, color="#33507a")
for i, s in enumerate(scores):
    if s > 0:
        ax.text(i, s + 0.006, f"{s:.3f}", ha="center", fontsize=8, fontweight="bold")
ax.text(len(runs) - 0.5, -0.062, "* = gemini-3.1-flash-lite driver (rest gemma-4-26b)",
        fontsize=7.5, ha="right", color="#555")
ax.set_ylabel("official verifier score")
ax.set_title("Figure 3 - Dev-run scores: plumbing fixes turn zeros into scored content; the outline planner lifts the ceiling",
             fontsize=10, pad=8)
ax.spines[["top", "right"]].set_visible(False)
fig.savefig(f"{OUT}/fig3_outcomes.png", dpi=170, bbox_inches="tight")
plt.close(fig)
print("figures done")
