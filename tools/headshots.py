"""Cut out Cobham headshots for the match day cards.

Usage:  python3 tools/headshots.py OUT_DIR photo1.jpg photo2.heic ...
Needs:  pip install "rembg[cpu]" pillow pillow-heif scipy numpy

Removes the backdrop (white sheet or green screen), strips green spill,
cleans the pale fringe, and scales so heads match the existing squad
(head width about 31% of image width, image about 1.28:1).
Output: one transparent PNG per input, 1000px wide, same base name.
"""
import sys, os, numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import binary_fill_holes, gaussian_filter
from PIL import ImageFilter
try:
    import pillow_heif; pillow_heif.register_heif_opener()
except ImportError:
    pass
from rembg import remove, new_session

HEAD_RATIO = 0.308
ASPECT = 1.28

def defringe(im, erode=3, feather=1.1):
    a = im.getchannel("A")
    a2 = a.filter(ImageFilter.MinFilter(erode*2+1)).filter(ImageFilter.GaussianBlur(feather))
    inner = (np.array(a.filter(ImageFilter.MinFilter(erode*4+3))) > 250).astype(np.float32)
    rgb = np.array(im.convert("RGB")).astype(np.float32)
    num = np.stack([gaussian_filter(rgb[..., c]*inner, 7) for c in range(3)], -1)
    den = gaussian_filter(inner, 7)[..., None]
    fill = np.where(den > 1e-3, num/np.maximum(den, 1e-3), rgb)
    out = np.where((inner < 0.5)[..., None], fill, rgb).clip(0, 255).astype("uint8")
    res = Image.fromarray(out, "RGB").convert("RGBA"); res.putalpha(a2); return res

def head_width(a):
    ys = np.where(a.max(1) > 128)[0]
    y = ys[0] + int((ys[-1]-ys[0])*0.22)
    xs = np.where(a[y] > 128)[0]
    return max(1, xs[-1]-xs[0])

def process(path, session):
    raw = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    arr = np.array(raw).astype(int)
    if np.median(arr[:50, :, 1] - np.maximum(arr[:50, :, 0], arr[:50, :, 2])) > 30:  # green screen
        arr[..., 1] = np.minimum(arr[..., 1], np.maximum(arr[..., 0], arr[..., 2]))
    im = Image.fromarray(arr.clip(0, 255).astype("uint8"))
    mask = np.array(remove(raw, session=session, only_mask=True, post_process_mask=True))
    m = mask > 20
    cols = np.where(m[-1])[0]
    if len(cols): m[-1, cols.min():cols.max()+1] = True
    filled = binary_fill_holes(m)
    out = im.convert("RGBA"); out.putalpha(Image.fromarray(np.where(filled & ~m, 255, mask).astype("uint8")))
    out = defringe(out)
    A = np.array(out.getchannel("A"))
    top = max(0, np.where(A.max(1) > 20)[0][0] - int(out.height*0.03))
    W = int(head_width(A)/HEAD_RATIO); H = int(W/ASPECT)
    crop = out.crop((0, top, out.width, min(out.height, top+H)))
    canvas = Image.new("RGBA", (max(W, crop.width), H), (0, 0, 0, 0))
    x0 = (canvas.width-crop.width)//2; canvas.alpha_composite(crop, (x0, 0))
    if x0 > 0:  # soften the cut shoulder edges when padding sideways
        ca = np.array(canvas).astype(float); fw = int(crop.width*0.10); r = np.linspace(0, 1, fw)
        ca[:, x0:x0+fw, 3] *= r[None, :]; ca[:, x0+crop.width-fw:x0+crop.width, 3] *= r[::-1][None, :]
        canvas = Image.fromarray(ca.clip(0, 255).astype("uint8"), "RGBA")
    s = min(1, 1000/canvas.width)
    return canvas.resize((int(canvas.width*s), int(canvas.height*s)), Image.LANCZOS)

if __name__ == "__main__":
    out_dir, files = sys.argv[1], sys.argv[2:]
    os.makedirs(out_dir, exist_ok=True)
    sess = new_session("u2net_human_seg")
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0] + ".png"
        process(f, sess).save(os.path.join(out_dir, name), optimize=True)
        print("done", name)
