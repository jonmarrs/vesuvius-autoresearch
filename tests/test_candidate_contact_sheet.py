import json

from PIL import Image

from scripts.archive.build_candidate_contact_sheet import build_contact_sheet


def test_build_candidate_contact_sheet(tmp_path):
    root = tmp_path / "evidence"
    for idx in range(3):
        candidate = root / f"candidate_{idx:03d}"
        predictions = candidate / "predictions"
        predictions.mkdir(parents=True)
        image_path = predictions / f"candidate_{idx:03d}.png"
        Image.new("RGB", (120, 40), (idx * 40, 10, 20)).save(image_path)
        (candidate / "manifest.json").write_text(
            json.dumps(
                {
                    "prediction_image": str(image_path),
                    "candidate": {
                        "scroll_id": "Scroll 2",
                        "division": "div_90",
                        "z": str(18000 + idx),
                        "review_score": "2.5",
                    },
                }
            )
        )

    out = tmp_path / "contact.png"
    result = build_contact_sheet(root, out, thumb_width=120, columns=2)

    assert result == {"out": str(out), "candidates": 3, "columns": 2, "rows": 2}
    assert out.exists()
    with Image.open(out) as sheet:
        assert sheet.size == (240, 148)
