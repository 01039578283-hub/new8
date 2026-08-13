from __future__ import annotations

import hashlib
import sys
from collections import Counter

import generate_high_grade_subject_pages as build
import high_grade_keyword_strategy as strategy


def main() -> None:
    rows = build.shared.read_csv(build.shared.COMMON / "센터정보 정리.csv")
    build.shared.enrich_center_rows(rows)
    errors: list[str] = []

    for config in build.CONFIGS:
        sources = build.load_sources(config)
        meta_values: list[str] = []
        heading_sets: list[tuple[str, ...]] = []
        question_sets: list[tuple[str, ...]] = []
        secondary_counts: Counter[str] = Counter()

        for raw, row in zip(sources, rows):
            local = build.shared.compact_text(row.get("근처 수업가능 동네"))
            title = f"{local} {config.category}"
            key = f"{title}|{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"
            primary = build.ranked_signals(raw, config, key)[0]
            plan = strategy.make_plan(
                category=config.category,
                grade=config.grade,
                subject=config.subject,
                local=local,
                primary_label=primary["label"],
                key=key,
                school_level=config.school_level,
            )
            sections = build.make_sections(raw, row, config, 0)
            meta = sections["메타설명"]
            headings = tuple(
                line[3:].strip()
                for line in sections["본문"].splitlines()
                if line.startswith("## ")
            )
            questions = tuple(
                line.split(". ", 1)[1].strip()
                for line in sections["FAQ"].splitlines()
                if line.startswith("Q") and ". " in line
            )

            if sections["페이지타이틀"] != f"{local} {plan.representative}":
                errors.append(f"{title}: representative keyword")
            if not all(value in meta for value in (local, plan.representative, plan.secondary)):
                errors.append(f"{title}: secondary keyword")
            if not headings or plan.detailed not in headings[0]:
                errors.append(f"{title}: detailed keyword heading")
            if not any(plan.issue in question for question in questions):
                errors.append(f"{title}: answer query")
            if not 70 <= len(meta) <= 100:
                errors.append(f"{title}: meta length={len(meta)}")
            if f"{plan.issue}는" in sections["FAQ"]:
                errors.append(f"{title}: malformed issue particle")

            meta_values.append(meta)
            heading_sets.append(headings)
            question_sets.append(questions)
            secondary_counts[plan.secondary] += 1

        expected = len(rows)
        if len(set(meta_values)) != expected:
            errors.append(f"{config.category}: duplicate meta")
        if len(set(heading_sets)) != expected:
            errors.append(f"{config.category}: duplicate heading set")
        if len(set(question_sets)) != expected:
            errors.append(f"{config.category}: duplicate question set")
        if len(secondary_counts) < 3:
            errors.append(f"{config.category}: secondary phrase distribution")

        print(
            f"{config.category}: pages={expected} meta={len(set(meta_values))} "
            f"headings={len(set(heading_sets))} FAQ={len(set(question_sets))} "
            f"secondary={dict(sorted(secondary_counts.items()))}"
        )

    if errors:
        print(f"keyword audit failed: {len(errors)} error(s)")
        for error in errors[:100]:
            print(f"- {error}")
        raise SystemExit(1)
    print("keyword audit passed")


if __name__ == "__main__":
    main()
