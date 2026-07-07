"""Probe MIM_paper_v1.mph geometry: up/down domains, pairs, feature list.

Run once, print everything, disconnect.  Standalone mph.Client (separate from
the MCP server's session - both connect to the same COMSOL server).
"""
import sys
import jpype as _jp
import mph

MODEL_PATH = r"C:\Users\陆星\Desktop\MIM_paper_v1.mph"

print("[probe] starting mph.Client ...")
client = mph.Client(cores=4)
print(f"[probe] connected: {client}")
m = client.load(MODEL_PATH)
mj = m.java
comp = mj.component("comp1")

# --- list geometry features ---
gl = comp.geom()
gtags = list(g.tags() for g in [gl])[0]
print("\n=== geometry features ===")
geom = comp.geom("geom1")
print(f"geom.feature().size() = {geom.feature().size()}")
for t in list(geom.feature().tags()):
    f = geom.feature().get(t)
    try:
        label = f.label()
    except Exception:
        label = "?"
    print(f"  tag={t}  label={label}")

# --- fin node ---
print("\n=== fin node ===")
try:
    fin = geom.feature().get("fin")
    print(f"fin found, action={fin.getString('action')}, createpairs={fin.getString('createpairs')}, imprint={fin.getString('imprint')}")
except Exception as e:
    print(f"fin get error: {e}")

# --- domains & boundaries ---
print("\n=== geometry stats ===")
print(f"NDomains    = {geom.getNDomains()}")
print(f"NBoundaries = {geom.getNBoundaries()}")
print(f"SDim        = {geom.getSDim()}")

# --- up/down per boundary ---
print("\n=== up/down per boundary ===")
ud = geom.getUpDown()
# ud is int[2][n_bnd]
n_bnd = geom.getNBoundaries()
print(f"getUpDown returned shape: outer={len(ud)}, inner0={len(ud[0]) if len(ud)>0 else 'NA'}, inner1={len(ud[1]) if len(ud)>1 else 'NA'}")
ups = list(ud[0])  # up domain per boundary
downs = list(ud[1])  # down domain per boundary
for i in range(n_bnd):
    print(f"  bnd {i+1}: up_dom={ups[i]}, down_dom={downs[i]}")

# --- face X / normal at center for each boundary (already known from MCP tool but include for completeness) ---
print("\n=== boundary centers + normals ===")
import jpype as _jpp
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

# --- pairs (if any) ---
print("\n=== pairs (geom pairs) ===")
try:
    pair_tags = list(geom.pair().tags()) if hasattr(geom, "pair") else []
    print(f"geom.pair().tags() = {pair_tags}")
except Exception as e:
    print(f"geom.pair() error: {e}")

print("\n=== component pairs / assembly pairs ===")
try:
    cp = comp.pair()
    ptags = list(cp.tags())
    print(f"comp.pair().tags() = {ptags}")
    for t in ptags:
        p = cp.get(t)
        try:
            print(f"  pair {t}: src={list(p.selection('src').entities()) if hasattr(p,'selection') else '?'}, dst={list(p.selection('dst').entities()) if hasattr(p,'selection') else '?'}")
        except Exception as e:
            print(f"  pair {t}: selection probe error {e}")
except Exception as e:
    print(f"comp.pair() error: {e}")

# --- domains listing ---
print("\n=== domain bounding boxes ===")
for d in range(1, geom.getNDomains() + 1):
    try:
        bb = list(geom.domainBB(d))
        print(f"  dom {d}: bbox={[float(x) for x in bb]}")
    except Exception as e:
        print(f"  dom {d}: bbox error {e}")

print("\n[probe] done.")
client.disconnect()
