"""Cut out Cobham headshots for the match day cards.

Usage:  python3 tools/headshots.py OUT_DIR photo1.jpg photo2.heic ...
Needs:  pip install "rembg[cpu]" pillow pillow-heif scipy numpy

Removes the backdrop (white sheet or green screen), strips green spill,
cleans the pale fringe, and scales so heads match the existing squad
(head width about 31% of image width, image about 1.28:1).
Output: one transparent PNG per input, 1000px wide, same base name.
Add --wall before the photos to strip white wall showing through messy hair
(only touches bluish white pixels in the top 30% near the edge, so skin is safe).
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
    ys = np.where(A.max(1) > 128)[0]; yh = ys[0] + int((ys[-1]-ys[0])*0.22)
    xs = np.where(A[yh] > 128)[0]; cx = (xs[0]+xs[-1])//2
    x1 = max(0, cx-W//2); x2 = min(out.width, cx+W//2)
    crop = out.crop((x1, top, x2, min(out.height, top+H)))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0 = x1-(cx-W//2); canvas.alpha_composite(crop, (x0, 0))
    pad_l, pad_r = x0 > 0, x0+crop.width < W
    if pad_l or pad_r:  # soften shoulders that end at the photo edge
        ca = np.array(canvas).astype(float); fw = int(crop.width*0.10); r = np.linspace(0, 1, fw)
        if pad_l: ca[:, x0:x0+fw, 3] *= r[None, :]
        if pad_r: ca[:, x0+crop.width-fw:x0+crop.width, 3] *= r[::-1][None, :]
        canvas = Image.fromarray(ca.clip(0, 255).astype("uint8"), "RGBA")
    s = min(1, 1000/canvas.width)
    return canvas.resize((int(canvas.width*s), int(canvas.height*s)), Image.LANCZOS)

def clean_wall(img):
    from scipy.ndimage import distance_transform_edt, binary_opening
    a = np.array(img).astype(float); r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    H = a.shape[0]; lum = 0.3*r+0.59*g+0.11*b
    dist = distance_transform_edt(al > 40)
    hair = np.zeros(al.shape, bool); hair[:int(H*0.30)] = True
    wall = hair & (dist < 60) & (b >= r-6) & (lum > 95)
    al2 = np.where(wall, al*np.clip((150-lum)/55, 0, 1), al)
    keep = binary_opening(al2 > 70, iterations=2) | (al2 > 220)
    a[..., 3] = np.where(hair & ~keep, 0, al2)
    return Image.fromarray(a.clip(0, 255).astype("uint8"), "RGBA")

if __name__ == "__main__":
    args = sys.argv[1:]; wall = "--wall" in args; args = [x for x in args if x != "--wall"]
    out_dir, files = args[0], args[1:]
    os.makedirs(out_dir, exist_ok=True)
    sess = new_session("u2net_human_seg")
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0] + ".png"
        img = process(f, sess)
        if wall: img = clean_wall(img)
        img.save(os.path.join(out_dir, name), optimize=True)
        print("done", name)
