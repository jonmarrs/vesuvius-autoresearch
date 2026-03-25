import os
import urllib.request

FILES = [
    # Frag 1
    ("local_data/PHercParis2Fr47/inklabels.png", "https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/working/54keV_exposed_surface/inklabels.png"),
    ("local_data/PHercParis2Fr47/mask.png", "https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/working/54keV_exposed_surface/mask.png"),
    # Frag 2
    ("local_data/PHercParis2Fr143/inklabels.png", "https://dl.ash2txt.org/fragments/Frag2/PHercParis2Fr143.volpkg/working/54keV_exposed_surface/inklabels.png"),
    ("local_data/PHercParis2Fr143/mask.png", "https://dl.ash2txt.org/fragments/Frag2/PHercParis2Fr143.volpkg/working/54keV_exposed_surface/mask.png"),
    # Frag 3
    ("local_data/PHercParis1Fr34/inklabels.png", "https://dl.ash2txt.org/fragments/Frag3/PHercParis1Fr34.volpkg/working/54keV_exposed_surface/inklabels.png"),
    ("local_data/PHercParis1Fr34/mask.png", "https://dl.ash2txt.org/fragments/Frag3/PHercParis1Fr34.volpkg/working/54keV_exposed_surface/mask.png"),
    # Frag 4
    ("local_data/PHercParis1Fr39/inklabels.png", "https://dl.ash2txt.org/fragments/Frag4/PHercParis1Fr39.volpkg/working/54keV_exposed_surface/PHercParis1Fr39_54keV_inklabels.png"),
    ("local_data/PHercParis1Fr39/mask.png", "https://dl.ash2txt.org/fragments/Frag4/PHercParis1Fr39.volpkg/working/54keV_exposed_surface/PHercParis1Fr39_54keV_mask.png"),
    # Frag 5
    ("local_data/PHerc1667Cr1Fr3/inklabels.png", "https://dl.ash2txt.org/fragments/Frag5/PHerc1667Cr1Fr3.volpkg/working/PHerc1667Cr01Fr03_70keV_3.24um/PHerc1667Cr01Fr03_70keV_inklabels.png"),
    ("local_data/PHerc1667Cr1Fr3/mask.png", "https://dl.ash2txt.org/fragments/Frag5/PHerc1667Cr1Fr3.volpkg/working/PHerc1667Cr01Fr03_70keV_3.24um/PHerc1667Cr01Fr03_70keV_mask.png"),
    # Frag 6
    ("local_data/PHerc51Cr4Fr8/inklabels.png", "https://dl.ash2txt.org/fragments/Frag6/PHerc51Cr4Fr8.volpkg/working/PHerc0051Cr04Fr08_53keV_3.24um/PHerc0051Cr04Fr08_53keV_inklabels.png"),
    ("local_data/PHerc51Cr4Fr8/mask.png", "https://dl.ash2txt.org/fragments/Frag6/PHerc51Cr4Fr8.volpkg/working/PHerc0051Cr04Fr08_53keV_3.24um/PHerc0051Cr04Fr08_53keV_mask.png"),
]

for out_path, url in FILES:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    print(f"Downloading {url} -> {out_path}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            with open(out_path, 'wb') as f:
                f.write(response.read())
    except Exception as e:
        print(f"  Failed: {e}")

