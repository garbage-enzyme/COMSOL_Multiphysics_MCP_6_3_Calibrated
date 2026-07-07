"""Final MIM patch metasurface build script.

Creates the Au-Al2O3-Au MIM patch thermal emitter model from the continuous-film
baseline, using the validated CopyFace mesh approach.

Output: C:\\Users\\陆星\\Desktop\\MIM_patch_final.mph
"""
import mph

MODEL = r"C:\Users\陆星\Desktop\MIM_paper_baseline_v1.mph"
OUT = r"C:\Users\陆星\Desktop\MIM_patch_final.mph"

# Paper parameters (Chen et al. 2023, IJTS 185: 108069)
P = 1.35e-6    # unit cell period (x & y)
L = 8.56e-7    # patch side (x & y, centered)
hp = 1.0e-7    # Au patch thickness (100 nm)
dp = 4.0e-8    # Al2O3 spacer thickness (40 nm)
H = 1.35e-6    # cell height

print("=" * 60)
print("MIM Patch Metasurface - Final Build")
print("=" * 60)

client = mph.Client(cores=4)
m = client.load(MODEL)
mj = m.java
comp = mj.component("comp1")
geom = comp.geom("geom1")

# --- 1. Add patch block (short, hp=100nm) ---
patch_pos = [(P - L) / 2, (P - L) / 2, dp]
b_pat = geom.feature().create("b_pat", "Block")
b_pat.set("size", [str(L), str(L), str(hp)])
b_pat.set("pos", [str(patch_pos[0]), str(patch_pos[1]), str(patch_pos[2])])
print(f"[1] Patch block: size=[{L},{L},{hp}], pos={patch_pos}")

# --- 2. Difference (keep patch as dom 3) ---
dif = geom.feature().create("dif1", "Difference")
dif.selection("input").set(["b_air"])
dif.selection("input2").set(["b_pat"])
dif.set("keepsubtract", True)
print("[2] Difference: air - patch, keep=True")

# --- 3. Build geometry (FormUnion) ---
geom.run()
n_dom = geom.getNDomains()
n_bnd = geom.getNBoundaries()
print(f"[3] Geometry: {n_dom} domains, {n_bnd} boundaries")

# --- 4. Identify boundaries ---
import jpype as _jp
ud = geom.getUpDown()
ups = list(ud[0])
downs = list(ud[1])
PP = _jp.JArray(_jp.JArray(_jp.JDouble))(1)
bnds = []
for i in range(1, n_bnd + 1):
    try:
        pr = list(geom.faceParamRange(i))
        u_mid = (float(pr[0]) + float(pr[1])) / 2.0
        v_mid = (float(pr[2]) + float(pr[3])) / 2.0
        PP[0] = _jp.JArray(_jp.JDouble)([u_mid, v_mid])
        normal = list(geom.faceNormal(i, PP)[0])
        center = list(geom.faceX(i, PP)[0])
        bnds.append({
            "num": i, "up": ups[i-1], "down": downs[i-1],
            "normal": [float(n) for n in normal],
            "center": [float(c) for c in center],
        })
    except:
        bnds.append({"num": i, "up": ups[i-1], "down": downs[i-1]})

# Patch footprint: up=3, down=1
patch_fp = [b["num"] for b in bnds if b.get("up") == 3 and b.get("down") == 1]
# Bottom: normal -z, z=0
bottom = [b["num"] for b in bnds if b.get("normal", [0,0,1])[2] < -0.5 and abs(b.get("center", [0,0,1])[2]) < 1e-15]
# Top: normal +z, z=H
top = [b["num"] for b in bnds if b.get("normal", [0,0,-1])[2] > 0.5 and abs(b.get("center", [0,0,0])[2] - H) < 1e-15]
# Side pairs: only EXTERIOR faces at x=0/P or y=0/P (not patch interior sides)
x_src = [b["num"] for b in bnds if b.get("normal", [1,0,0])[0] < -0.5 and abs(b.get("center", [1,0,0])[0]) < 1e-15]
x_dst = [b["num"] for b in bnds if b.get("normal", [-1,0,0])[0] > 0.5 and abs(b.get("center", [P,0,0])[0] - P) < 1e-15]
y_src = [b["num"] for b in bnds if b.get("normal", [0,1,0])[1] < -0.5 and abs(b.get("center", [0,0,0])[1]) < 1e-15]
y_dst = [b["num"] for b in bnds if b.get("normal", [0,-1,0])[1] > 0.5 and abs(b.get("center", [0,P,0])[1] - P) < 1e-15]

print(f"[4] patch_footprint={patch_fp}, bottom={bottom}, top={top}")
print(f"    x_src={x_src}, x_dst={x_dst}, y_src={y_src}, y_dst={y_dst}")

# --- 5. Update BCs ---
ewfd = comp.physics().get("ewfd")

# LayeredTransition -> patch footprint
ltr = ewfd.feature().get("ltr1")
ltr.selection().set(patch_fp)
print(f"[5] LayeredTransition -> {patch_fp}")

# LayeredImpedance -> bottom
lib = ewfd.feature().get("lib1")
lib.selection().set(bottom)
print(f"    LayeredImpedance -> {bottom}")

# PeriodicStructure port -> top
ps = ewfd.feature().get("ps1")
try:
    ps.selection("excitedPortSelection").set(top)
    print(f"    PeriodicStructure port -> {top}")
except:
    print(f"    Port auto-detected (top={top})")

# Air material -> dom 3
mat_air = comp.material().get("mat_air")
cur = list(mat_air.selection().entities())
if 3 not in cur:
    mat_air.selection().set(cur + [3])
    print(f"    Air material -> domains {cur + [3]}")

# --- 6. Create CopyFace mesh ---
mesh_list = comp.mesh()
for mt in list(mesh_list.tags()):
    mesh_list.remove(mt)

mesh = mesh_list.create("mesh1")

# FreeTri on source side faces
if x_src:
    ftx = mesh.feature().create("ftri_x", "FreeTri")
    ftx.selection().set(x_src)
if y_src:
    fty = mesh.feature().create("ftri_y", "FreeTri")
    fty.selection().set(y_src)

# CopyFace: source -> destination (identical periodic meshes)
if x_src and x_dst:
    cpx = mesh.feature().create("cp_x", "CopyFace")
    try:
        cpx.selection("source").set(x_src)
        cpx.selection("destination").set(x_dst)
    except:
        cpx.selection().set(x_src + x_dst)

if y_src and y_dst:
    cpy = mesh.feature().create("cp_y", "CopyFace")
    try:
        cpy.selection("source").set(y_src)
        cpy.selection("destination").set(y_dst)
    except:
        cpy.selection().set(y_src + y_dst)

# FreeTet for volume
ft = mesh.feature().create("ft1", "FreeTet")
mesh.run()
print(f"[6] Mesh: FreeTri+CopyFace+FreeTet -> {mesh.getNumElem()} elements")

# --- 7. Solve ---
print("[7] Solving (10 wavelengths: 1-10 um)...")
mj.study("std1").run()
print("    Solve completed!")

# --- 8. Evaluate ---
print("[8] Evaluating Rtotal/Ttotal/Atotal vs wl...")
results = m.evaluate(["ewfd.Rtotal", "ewfd.Ttotal", "ewfd.Atotal", "wl"])
print(f"\n    {'wl(um)':>8}  {'R':>10}  {'T':>10}  {'A':>10}  {'eps=1-R':>10}")
print(f"    {'-'*8}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")
for row in results:
    wl_um = float(row[3]) * 1e6
    r, t, a = float(row[0]), float(row[1]), float(row[2])
    eps = 1 - r
    print(f"    {wl_um:8.2f}  {r:10.6f}  {t:10.6f}  {a:10.6f}  {eps:10.6f}")

# --- 9. Save ---
m.save(OUT)
print(f"\n[9] Saved to {OUT}")

print("\n" + "=" * 60)
print("Done! Model ready for analysis.")
print("=" * 60)

try:
    client.disconnect()
except:
    pass
