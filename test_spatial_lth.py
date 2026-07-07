"""Test spatially-varying lth on LayeredTransition BC (no geometry change!).

Strategy: load baseline (2 domains, Sweep mesh), modify LayeredTransition BC's
lth to spatial expression: hp on patch footprint, 0 elsewhere.
If lth=0 → identity (no effect), so only patch footprint has Au thin film.
"""
import mph

MODEL = r"C:\Users\陆星\Desktop\MIM_paper_baseline_v1.mph"
OUT = r"C:\Users\陆星\Desktop\MIM_patch_spatial_lth.mph"

# Paper parameters
P = 1.35e-6
L = 8.56e-7
hp = 1.0e-7
dp = 4.0e-8
H = 1.35e-6

# Patch footprint xy range
px_min = (P - L) / 2  # 2.47e-7
px_max = (P + L) / 2  # 1.103e-6

# Spatial lth expression: hp on patch footprint, 0 elsewhere
# COMSOL if syntax: if(condition, true_val, false_val)
# Need to handle 2D (x AND y in range)
lth_expr = f"if((x>{px_min})&&(x<{px_max})&&(y>{px_min})&&(y<{px_max}),{hp},0)"
print(f"Spatial lth expression: {lth_expr}")

print("[1] Loading baseline model...")
client = mph.Client(cores=4)
m = client.load(MODEL)
mj = m.java
comp = mj.component("comp1")

# Find ewfd physics
phys = comp.physics()
print(f"  physics tags: {list(phys.tags())}")
ewfd = None
try:
    ewfd = phys.get("ewfd")
    print(f"  ewfd found by tag 'ewfd'")
except:
    for t in list(phys.tags()):
        p = phys.get(t)
        ewfd = p
        print(f"  using physics tag: {t}")
        break

# Find LayeredTransition BC
ltr = None
print(f"  ewfd feature tags: {list(ewfd.feature().tags())}")
for t in list(ewfd.feature().tags()):
    f = ewfd.feature().get(t)
    try:
        # Check by tag name (ltr1) or by feature type
        if t == "ltr1" or "LayeredTransition" in t:
            ltr = f
            print(f"  LayeredTransition tag: {t}")
            break
    except:
        pass
if ltr is None:
    # Try getting ltr1 directly
    try:
        ltr = ewfd.feature().get("ltr1")
        print(f"  LayeredTransition found by tag 'ltr1'")
    except Exception as e:
        print(f"  ERROR: Could not find LayeredTransition: {e}")

# Get current lth
try:
    cur_lth = str(ltr.getString("lth"))
    print(f"  Current lth: {cur_lth}")
except Exception as e:
    print(f"  getString(lth) error: {e}")

# Set spatial lth
print(f"\n[2] Setting lth to spatial expression...")
try:
    ltr.set("lth", lth_expr)
    print(f"  Set lth = {lth_expr}")
    # Verify
    new_lth = str(ltr.getString("lth"))
    print(f"  Verified lth = {new_lth}")
except Exception as e:
    print(f"  ERROR setting lth: {e}")

# Also try setting relpermittivity to spatial expression (Drude on patch, 1 on rest)
au_drude = "1-(1.37e16)^2/((2*pi*c_const/wl)*((2*pi*c_const/wl)+i*4.1e13))"
eps_expr = f"if((x>{px_min})&&(x<{px_max})&&(y>{px_min})&&(y<{px_max}),{au_drude},1)"
print(f"\n[3] Setting relpermittivity to spatial expression...")
try:
    ltr.set("relpermittivity", eps_expr)
    print(f"  Set relpermittivity = {eps_expr[:80]}...")
    new_eps = str(ltr.getString("relpermittivity"))
    print(f"  Verified relpermittivity = {new_eps[:80]}...")
except Exception as e:
    print(f"  ERROR setting relpermittivity: {e}")
    # Try setting on the LML shell instead
    print("  Trying LML shell group...")
    try:
        mat_list = comp.material()
        for mt in list(mat_list.tags()):
            mat = mat_list.get(mt)
            if "lml" in mt.lower():
                print(f"  Found LML: {mt}")
                sh = mat.propertyGroup("shell")
                sh.set("lth", lth_expr)
                print(f"  Set LML shell lth = {lth_expr}")
                sh.set("relpermittivity", eps_expr)
                print(f"  Set LML shell relpermittivity = {eps_expr[:80]}...")
                break
    except Exception as e2:
        print(f"  LML shell error: {e2}")

# Solve
print(f"\n[4] Solving...")
try:
    mj.study("std1").run()
    print("  Solve completed!")
except Exception as e:
    print(f"  Solve error: {e}")

# Evaluate
print(f"\n[5] Evaluating Rtotal vs wl...")
try:
    results = m.evaluate(["ewfd.Rtotal", "wl"])
    print(f"  Results: {len(results)} points")
    for row in results:
        if hasattr(row, '__len__') and len(row) >= 2:
            wl_um = float(row[1]) * 1e6
            r = float(row[0])
            print(f"    wl={wl_um:.2f} µm  R={r:.6f}  eps={1-r:.6f}")
except Exception as e:
    print(f"  Evaluate error: {e}")

# Save
print(f"\n[6] Saving...")
try:
    m.save(OUT)
    print(f"  Saved to {OUT}")
except Exception as e:
    print(f"  Save error: {e}")

print("\nDone!")
try:
    client.disconnect()
except:
    pass
