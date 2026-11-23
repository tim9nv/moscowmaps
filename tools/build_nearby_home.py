"""Build the address-neighbourhood index from the Atlas transport and ecology maps."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def constant(path, name):
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(rf"^const {name}\s*=\s*", text, re.M)
    if not match:
        raise ValueError(f"{path}: missing {name}")
    return json.JSONDecoder().raw_decode(text[match.end():])[0]


stations = constant("assets/atlas.js", "METRO")["s"]
ecology = constant("ecology.html", "DATA")["sources"]
index = {"stations": [[lon, lat, kind, name] for lon, lat, _, kind, name in stations],
         "ecology": [{field: site[field] for field in ("n", "t", "lon", "lat")} for site in ecology]}
(ROOT / "assets/nearby-home.json").write_text(
    json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


sitemap = ROOT / "sitemap.xml"
document = sitemap.read_text(encoding="utf-8")
url = "https://www.mskatlas.ru/nearby-home.html"
if f"<loc>{url}</loc>" not in document:
    sitemap.write_text(document.replace("</urlset>", f"  <url><loc>{url}</loc></url>\n</urlset>"),
                       encoding="utf-8", newline="\n")
