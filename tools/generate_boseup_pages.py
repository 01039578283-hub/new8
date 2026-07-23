from pathlib import Path

import generate_korean_english_math_pages as generator
from boseup_content_variation import prepare_boseup_source_copy


generator.ZIP_PATH = (
    Path.home() / "Desktop" / "코칭센터.com 추가 원고" / "보습학원.zip"
)
generator.CATEGORY = "보습학원"
generator.prepare_detail_copy = lambda sections, row: prepare_boseup_source_copy(
    generator,
    sections,
    row,
)


if __name__ == "__main__":
    generator.main()
