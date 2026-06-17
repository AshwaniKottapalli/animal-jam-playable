#!/usr/bin/env python3
"""
Single-file HTML bundler for Animal Jam playable ad.
Inlines all JS (resolving ES module imports) and base64-encodes all assets.
Output: dist/index.html
"""

import os, re, base64, mimetypes, json

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
os.makedirs(DIST, exist_ok=True)

# ── 1. Collect all assets → base64 data URLs ─────────────────────────────────

ASSET_EXTS = {'.png','.jpg','.jpeg','.webp','.mp3','.otf','.ttf','.json'}
assets = {}  # "assets/foo/bar.png" -> "data:image/png;base64,..."

def mime(path):
    ext = os.path.splitext(path)[1].lower()
    return {
        '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg',
        '.webp':'image/webp', '.mp3':'audio/mpeg',
        '.otf':'font/otf', '.ttf':'font/ttf',
        '.json':'application/json',
    }.get(ext, 'application/octet-stream')

for dirpath, _, files in os.walk(ROOT):
    for fname in files:
        full = os.path.join(dirpath, fname)
        ext  = os.path.splitext(fname)[1].lower()
        if ext not in ASSET_EXTS:
            continue
        rel = os.path.relpath(full, ROOT).replace('\\', '/')
        # Skip src/, node_modules, dist, dev tools
        if any(rel.startswith(p) for p in ('src/','node_modules/','dist/','build.py')):
            continue
        with open(full, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('ascii')
        assets[rel] = f'data:{mime(full)};base64,{b64}'
        print(f'  {rel}: {len(data)//1024}KB → data URL')

# ── 2. Bundle JS modules (topological order) ─────────────────────────────────

# Dependency order — list files in the order they must be defined
MODULE_ORDER = [
    'src/tween.js',
    'src/atlas.js',
    'src/audio.js',
    'src/particles.js',
    'src/renderer.js',
    'src/ui.js',
    'src/config.js',
    'src/game.js',
    'src/main.js',
]

def process_js(path):
    with open(os.path.join(ROOT, path)) as f:
        src = f.read()
    # Strip import lines entirely (all symbols will be in scope from concatenation)
    src = re.sub(r'^import\s+.*?from\s+[\'"][^\'\"]+[\'"].*$', '', src, flags=re.MULTILINE)
    # Strip 'export' keyword from declarations (keep the declaration)
    src = re.sub(r'\bexport\s+default\s+', '', src)
    src = re.sub(r'\bexport\s+(class|function|const|let|var|async)\b', r'\1', src)
    # Strip bare export { ... } lines
    src = re.sub(r'^export\s*\{[^}]*\};?\s*$', '', src, flags=re.MULTILINE)
    return src

js_bundle = '\n'.join(process_js(p) for p in MODULE_ORDER)

# ── 3. Patch asset loading in the bundle ─────────────────────────────────────

asset_map_js = 'const __A=' + json.dumps(assets, separators=(',',':')) + ';'

# Patch: intercept fetch() for JSON atlas files and audio
# Patch: intercept Image src setter for image assets
patch_js = r"""
(function(){
  const _fetch = window.fetch.bind(window);
  window.fetch = function(url, opts) {
    const k = String(url).replace(/^\.?\/?/, '');
    for (const ak of Object.keys(__A)) {
      if (ak === k || ak.endsWith('/'+k.split('/').pop()) && ak.includes(k.split('/').slice(-2).join('/'))) {
        const d = __A[ak];
        if (d.startsWith('data:application/json')) {
          const text = atob(d.split(';base64,')[1]);
          return Promise.resolve(new Response(text, {status:200,headers:{'Content-Type':'application/json'}}));
        }
        return _fetch(d, opts);
      }
    }
    return _fetch(url, opts);
  };
  const _desc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,'src');
  Object.defineProperty(HTMLImageElement.prototype,'src',{
    set(v){
      const k = String(v).replace(/^\.?\/?/,'');
      for(const ak of Object.keys(__A)){
        if(ak===k || (k.length>5 && ak.endsWith('/'+k.split('/').pop()))){
          _desc.set.call(this,__A[ak]); return;
        }
      }
      _desc.set.call(this,v);
    },
    get(){ return _desc.get.call(this); }
  });
})();
"""

# ── 4. Read original HTML, inject everything ─────────────────────────────────

with open(os.path.join(ROOT, 'index.html')) as f:
    html = f.read()

# Remove <link rel="preload"> font lines (fonts now in __A)
html = re.sub(r'\s*<link rel="preload"[^>]+>\s*', '\n', html)

# Remove the <script type="module" src="src/main.js"> tag
html = re.sub(r'\s*<script[^>]+src=["\']src/main\.js["\'][^>]*>\s*</script>', '', html)

# Inject bundled script before </body>
inline_script = f'<script>\n{asset_map_js}\n{patch_js}\n{js_bundle}\n</script>'
html = html.replace('</body>', f'{inline_script}\n</body>')

out_path = os.path.join(DIST, 'index.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

size = os.path.getsize(out_path)
print(f'\n✓ dist/index.html: {size/1024/1024:.2f}MB ({size:,} bytes)')
if size > 5*1024*1024:
    print(f'  ⚠️  Exceeds 5MB limit by {(size-5*1024*1024)//1024}KB')
else:
    print(f'  ✅ Under 5MB limit ({(5*1024*1024-size)//1024}KB to spare)')
