from pathlib import Path

import generate_korean_english_math_pages as generator


generator.ZIP_PATH = (
    Path.home() / "Desktop" / "코칭센터.com 추가 원고" / "보습학원.zip"
)
generator.CATEGORY = "보습학원"
generator.prepare_detail_copy = generator.prepare_source_copy


if __name__ == "__main__":
    generator.main()
