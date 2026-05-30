import os
import urllib.request

FRAGS = {
    "Frag1": "PHercParis2Fr47",
    "Frag2": "PHercParis2Fr143",
    "Frag3": "PHercParis1Fr34",
    "Frag4": "PHercParis1Fr39",
    "Frag5": "PHerc1667Cr1Fr3",
    "Frag6": "PHerc51Cr4Fr8",
}

BASE_URL = "https://dl.ash2txt.org/fragments/"

for f_id, vol_name in FRAGS.items():
    print(f"Processing {f_id} ({vol_name})...")
    url = f"{BASE_URL}{f_id}/{vol_name}.volpkg/working/54keV_exposed_surface/"
    out_dir = f"local_data/{vol_name}"
    os.makedirs(out_dir, exist_ok=True)

    for file in ["inklabels.png", "mask.png"]:
        file_url = f"{url}{file}"
        out_path = os.path.join(out_dir, file)
        print(f"  Downloading {file_url} -> {out_path}")
        try:
            req = urllib.request.Request(file_url)
            with urllib.request.urlopen(req) as response:
                with open(out_path, "wb") as f:
                    f.write(response.read())
        except Exception as e:
            print(f"  Failed: {e}")
