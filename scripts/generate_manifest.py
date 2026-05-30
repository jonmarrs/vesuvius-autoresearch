import os


def get_dir_size(path):
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += get_dir_size(entry.path)
    return total


def generate():
    if not os.path.exists("local_data"):
        print("local_data doesn't exist")
        return

    with open("local_data_manifest.md", "w") as f:
        f.write("# Local Data Manifest\n\n")
        f.write(
            "This document lists the offline datasets currently built and stored in `local_data/`. "
        )
        f.write(
            "These datasets are completely excluded from git due to their massive size (~63GB total). "
        )
        f.write(
            "To regenerate these datasets locally, you must run the download scripts provided in this repository.\n\n"
        )

        f.write("## Generated 1GB Continuous Cross-Scroll Datasets\n\n")
        f.write("| Dataset | Size | Status |\n")
        f.write("|---|---|---|\n")

        for item in sorted(os.listdir("local_data")):
            path = os.path.join("local_data", item)
            if os.path.isdir(path) and item.endswith("_1GB"):
                size_mb = get_dir_size(path) / (1024 * 1024)
                if size_mb > 100:
                    f.write(f"| `{item}` | {size_mb:.2f} MB | Ready |\n")

        f.write("\n## Sub-sectional Division Datasets (11x 1GB Splits)\n\n")
        f.write(
            "These represent 1GB slices taken at 10% depth intervals through the full scroll volumes to ensure diverse topological representation.\n\n"
        )

        f.write("| Dataset | Scroll | Division |\n")
        f.write("|---|---|---|\n")

        for item in sorted(os.listdir("local_data")):
            if item.endswith("_1GB") and "_div_" in item:
                parts = item.split("_")
                scroll = parts[0]
                div = parts[2]
                f.write(f"| `{item}` | {scroll} | {div}% |\n")


if __name__ == "__main__":
    generate()
