"""Scrollable PDF page viewer with page navigation, rendered as one self-contained HTML block."""
import base64

import pymupdf

TEMPLATE = """
<style>
  body { margin: 0; font-family: sans-serif; font-size: 14px; color: #222; }
  #bar { height: 40px; display: flex; align-items: center; justify-content: center; gap: 8px;
         background: #f0f2f6; border-bottom: 1px solid #ccc; }
  #bar button { font-size: 14px; padding: 2px 10px; cursor: pointer; }
  #num { width: 52px; font-size: 14px; text-align: center; }
  #pages { position: relative; height: calc(100vh - 41px); overflow-y: auto; scroll-behavior: smooth; background: #888; }
  #pages img { display: block; width: 100%; margin-bottom: 8px; }
</style>
<div id="bar">
  <button id="prev" title="Previous page">&#9664;</button>
  <span>Page</span><input id="num" type="number" min="1" max="__N__" value="1"><span>of __N__</span>
  <button id="next" title="Next page">&#9654;</button>
</div>
<div id="pages">__IMGS__</div>
<script>
  const box = document.getElementById("pages"), num = document.getElementById("num");
  const imgs = [...box.querySelectorAll("img")];
  // The current page is the one crossing the middle of the visible area.
  const current = () => {
    const mid = box.scrollTop + box.clientHeight / 2;
    let n = 1;
    imgs.forEach((img, i) => { if (img.offsetTop <= mid) n = i + 1; });
    return n;
  };
  const go = n => {
    n = Math.min(Math.max(n, 1), imgs.length);
    box.scrollTo({ top: imgs[n - 1].offsetTop });
  };
  box.addEventListener("scroll", () => { if (document.activeElement !== num) num.value = current(); });
  num.addEventListener("change", () => { go(+num.value); num.blur(); });
  document.getElementById("prev").onclick = () => go(current() - 1);
  document.getElementById("next").onclick = () => go(current() + 1);
</script>
"""


def viewer_html(path):
    imgs = [
        '<img src="data:image/jpeg;base64,%s">'
        % base64.b64encode(page.get_pixmap(dpi=110).tobytes("jpeg", jpg_quality=75)).decode()
        for page in pymupdf.open(path)
    ]
    return TEMPLATE.replace("__N__", str(len(imgs))).replace("__IMGS__", "".join(imgs))
