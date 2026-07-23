from pathlib import Path

import audit_korean_english_math_pages as audit
from boseup_content_variation import prepare_boseup_source_copy


audit.ZIP_PATH = (
    Path.home() / "Desktop" / "코칭센터.com 추가 원고" / "보습학원.zip"
)
audit.CATEGORY = "보습학원"
audit.TARGET = audit.SITE / audit.PARENT / audit.CATEGORY
audit.generator.ZIP_PATH = audit.ZIP_PATH
audit.generator.CATEGORY = audit.CATEGORY
audit.generator.prepare_detail_copy = (
    lambda sections, row: prepare_boseup_source_copy(
        audit.generator,
        sections,
        row,
    )
)


if __name__ == "__main__":
    audit.main()
