"""Switch fin to createpairs=on, rebuild, probe pairs + boundaries.

Standalone mph.Client (separate from MCP server session).
"""
import mph
import jpype as _jpp

MODEL_PATH = r"C:\Users\陆星\Desktop\MIM_paper_v1.mph"
OUT_PATH = r"C:\Users\陆星\Desktop\MIM_paper_v1_pairs.mph"

print("[probe] starting mph.Client ...")
client = mph.Client(cores=4)
m = client.load(MODEL_PATH)
mj = m.java
comp = mj.component("comp1")
geom = comp.geom("geom1")

# --- switch fin to createpairs=on ---
fin = geom.feature().get("fin")
print(f"before: action={fin.getString('action')}, createpairs={fin.getString('createpairs')}, imprint={fin.getString('imprint')}")
fin.set("createpairs", "on")
print(f"after:  action={fin.getString('action')}, createpairs={fin.getString('createpairs')}, imprint={fin.getString('imprint')}")
geom.run()
print("[probe] geometry rebuilt.")

# --- stats ---
print(f"\nNDomains    = {geom.getNDomains()}")
print(f"NBoundaries = {geom.getNBoundaries()}")

# --- pairs ---
print("\n=== component pairs ===")
cp = comp.pair()
ptags = list(cp.tags())
print(f"comp.pair().tags() = {ptags}")
for t in ptags:
    p = cp.get(t)
    try:
        label = p.label()
    except Exception:
        label = "?"
    # probe src/dst
    src_ents = []
    dst_ents = []
    try:
        src_ents = list(p.selection('src').entities())
    except Exception as e:
        src_ents = f"err:{e}"
    try:
        dst_ents = list(p.selection('dst').entities())
    except Exception as e:
        dst_ents = f"err:{e}"
    print(f"  pair {t} ({label}): src={src_ents}, dst={dst_ents}")

# --- up/down per boundary ---
print("\n=== up/down per boundary ===")
n_bnd = geom.getNBoundaries()
ud = geom.getUpDown()
ups = list(ud[0])
downs = list(ud[1])
PP = _jpp.JArray(_jpp.JArray(_jpp.JDouble))(1)
for i in range(1, n_bnd + 1):
    try:
        pr = list(geom.faceParamRange(i))
        u_mid = (float(pr[0]) + float(pr[1])) / 2.0
        v_mid = (float(pr[2]) + float(pr[3])) / 2.0
        PP[0] = _jpp.JArray(_jpp.JDouble)([u_mid, v_mid])
        nx, ny, nz = list(geom.faceNormal(i, PP)[0])
        cx, cy, cz = list(geom.faceX(i, PP)[0])
        print(f"  bnd {i}: up={ups[i-1]}, down={downs[i-1]}, normal=({nx:.2f},{ny:.2f},{nz:.2f}), center=({cx:.3e},{cy:.3e},{cz:.3e})")
    except Exception as e:
        print(f"  bnd {i}: probe error {e}")

# --- save ---
m.save(OUT_PATH)
print(f"\n[probe] saved to {OUT_PATH}")
print("[probe] done.")
try:
    client.disconnect()
except Exception:
    pass
