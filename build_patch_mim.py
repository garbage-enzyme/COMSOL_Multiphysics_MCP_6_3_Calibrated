"""Build MIM patch model from baseline: add patch geometry, update BCs, solve.

Strategy: load MIM_paper_baseline_v1.mph (has complete ewfd physics + materials +
mesh + study), add a patch Block + Difference to the geometry, switch to
FormUnion (automatic continuity), update LayeredTransition BC to patch footprint
interface, assign air material to patch domain, rebuild mesh, solve, evaluate.

Run standalone (separate mph.Client from MCP server).
"""
import sys
import mph
import jpype as _jpp

MODEL_BASELINE = r"C:\Users\陆星\Desktop\MIM_paper_baseline_v1.mph"
OUT_PATH = r"C:\Users\陆星\Desktop\MIM_patch_v1.mph"

# Paper parameters (Chen et al. 2023)
P = 1.35e-6    # unit cell period
L = 8.56e-7    # patch side
hp = 1.0e-7    # Au patch thickness (100nm)
dp = 4.0e-8    # Al2O3 spacer thickness (40nm)
H = 1.35e-6    # cell height (air height = H - dp)

# Au Drude expression (wl parameter, NOT ewfd.freq — avoids impedance singularity)
au_drude = "1-(1.37e16)^2/((2*pi*c_const/wl)*((2*pi*c_const/wl)+i*4.1e13))"

def JArray_double(lst):
    return _jpp.JArray(_jpp.JDouble)(lst)

def JArray_int(lst):
    return _jpp.JArray(_jpp.JInt)([int(x) for x in lst])

def get_block_size(geom, tag):
    """Get block size as floats."""
    f = geom.feature().get(tag)
    sz_raw = str(f.getString("size"))  # Java String -> Python str
    # size is comma or space separated expressions like "1.35E-6,1.35E-6,4E-8"
    parts = sz_raw.replace(",", " ").split()
    return [float(p) for p in parts]

def get_block_pos(geom, tag):
    """Get block position as floats."""
    f = geom.feature().get(tag)
    pos_raw = str(f.getString("pos"))
    parts = pos_raw.replace(",", " ").split()
    return [float(p) for p in parts]

def identify_boundaries(geom):
    """Identify key boundaries by normal + center coordinates.
    Returns dict with boundary numbers for: bottom, top, patch_footprint_interface,
    al2_air_rest_interface, patch_top, patch_sides, cell_sides.
    """
    n_bnd = geom.getNBoundaries()
    ud = geom.getUpDown()
    ups = list(ud[0])
    downs = list(ud[1])

    PP = _jpp.JArray(_jpp.JArray(_jpp.JDouble))(1)
    bnds = []
    for i in range(1, n_bnd + 1):
        try:
            pr = list(geom.faceParamRange(i))
            u_mid = (float(pr[0]) + float(pr[1])) / 2.0
            v_mid = (float(pr[2]) + float(pr[3])) / 2.0
            PP[0] = _jpp.JArray(_jpp.JDouble)([u_mid, v_mid])
            normal = list(geom.faceNormal(i, PP)[0])
            center = list(geom.faceX(i, PP)[0])
            bnds.append({
                "num": i,
                "up": ups[i-1],
                "down": downs[i-1],
                "normal": [float(n) for n in normal],
                "center": [float(c) for c in center],
            })
        except Exception as e:
            bnds.append({"num": i, "error": str(e)})

    # Bottom: z=0, normal -z
    bottom = [b for b in bnds if b.get("normal", [0,0,1])[2] < -0.5 and abs(b.get("center", [0,0,1])[2]) < 1e-15]
    # Top: z=H, normal +z
    top = [b for b in bnds if b.get("normal", [0,0,-1])[2] > 0.5 and abs(b.get("center", [0,0,0])[2] - H) < 1e-15]

    # z=dp interface: boundaries at z≈dp with normal ±z
    z_dp_bnds = [b for b in bnds if abs(b.get("center", [0,0,0])[2] - dp) < 1e-15 and abs(b.get("normal", [0,0,0])[2]) > 0.5]

    # Patch footprint interface: z=dp, up=3 (patch dom), down=1 (Al2O3 dom)
    patch_footprint = [b for b in z_dp_bnds if b.get("up") == 3 and b.get("down") == 1]
    # Rest of z=dp interface: up=2 (air dom), down=1 (Al2O3 dom)
    al2_air_rest = [b for b in z_dp_bnds if b.get("up") == 2 and b.get("down") == 1]

    # Cell sides: normal ±x or ±y, at x=0/P or y=0/P
    cell_sides = [b for b in bnds if abs(abs(b.get("normal", [0,1,0])[0]) - 1) < 0.5 or abs(abs(b.get("normal", [0,1,0])[1]) - 1) < 0.5]

    result = {
        "bottom": [b["num"] for b in bottom],
        "top": [b["num"] for b in top],
        "patch_footprint_interface": [b["num"] for b in patch_footprint],
        "al2_air_rest_interface": [b["num"] for b in al2_air_rest],
        "z_dp_all": [b["num"] for b in z_dp_bnds],
        "all": bnds,
    }
    return result


print("=" * 60)
print("MIM Patch Model Build Script")
print("=" * 60)

print("\n[1] Loading baseline model...")
client = mph.Client(cores=4)
m = client.load(MODEL_BASELINE)
mj = m.java
comp = mj.component("comp1")
geom = comp.geom("geom1")
print(f"    loaded: {m}")

# --- Get existing geometry block tags ---
print("\n[2] Inspecting existing geometry features...")
tags = list(geom.feature().tags())
print(f"    tags: {tags}")

# Identify air block (large z-size) and Al2O3 block (small z-size)
air_tag = None
al2_tag = None
for t in tags:
    if t == "fin":
        continue
    f = geom.feature().get(t)
    try:
        sz = get_block_size(geom, t)
        print(f"    tag={t}, label={f.label()}, size={sz}")
        if sz[2] > 1e-7:  # air block (H-dp ≈ 1.31µm)
            air_tag = t
        else:  # Al2O3 block (dp=40nm)
            al2_tag = t
    except Exception as e:
        print(f"    tag={t}: error getting size: {e}")

if not air_tag or not al2_tag:
    print("    ERROR: Could not identify air/Al2O3 blocks!")
    sys.exit(1)
print(f"    -> air block tag: {air_tag}")
print(f"    -> Al2O3 block tag: {al2_tag}")

# --- Add patch block ---
# NOTE: patch extends to TOP of cell (z=dp to z=H), not just hp.
# This ensures all 3 domains have constant cross-sections → Sweep mesh works.
# The patch domain is AIR (same as dom 2). The Au thin film is modeled by
# LayeredTransition BC on the Al2O3/patch interface (z=dp, patch footprint).
# The patch height hp only affects the LayeredTransition thickness, not the geometry.
print("\n[3] Adding patch block (extends to top of cell for sweep mesh)...")
patch_pos = [(P - L) / 2, (P - L) / 2, dp]
patch_height = H - dp  # extend to top of cell (for constant cross-section)
b_pat = geom.feature().create("b_pat", "Block")
b_pat.set("size", [str(L), str(L), str(patch_height)])
b_pat.set("pos", [str(patch_pos[0]), str(patch_pos[1]), str(patch_pos[2])])
print(f"    patch block: size=[{L},{L},{patch_height}], pos={patch_pos}")

# --- Add Difference (subtract patch from air, keep patch) ---
print("\n[4] Adding Difference operation...")
dif = geom.feature().create("dif1", "Difference")
dif.selection("input").set([air_tag])
dif.selection("input2").set(["b_pat"])
try:
    dif.set("keepsubtract", True)
    print("    keepsubtract=True (property name 'keepsubtract' works)")
except Exception:
    try:
        dif.set("keep", True)
        print("    keep=True (property name 'keep')")
    except Exception as e2:
        print(f"    WARNING: could not set keep property: {e2}")
        print("    (patch might not survive as separate domain)")

# --- Check fin mode (should be FormUnion by default) ---
print("\n[5] Checking fin mode...")
try:
    fin = geom.feature().get("fin")
    action = fin.getString("action")
    print(f"    fin action = {action}")
    if action != "union" and action is not None:
        print("    Setting fin to FormUnion...")
        fin.set("action", "union")
except Exception as e:
    print(f"    fin check: {e} (no fin node, FormUnion is default)")

# --- Build geometry ---
print("\n[6] Building geometry...")
geom.run()
n_dom = geom.getNDomains()
n_bnd = geom.getNBoundaries()
print(f"    NDomains = {n_dom}, NBoundaries = {n_bnd}")
if n_dom != 3:
    print(f"    WARNING: Expected 3 domains, got {n_dom}!")

# --- Identify key boundaries ---
print("\n[7] Identifying key boundaries...")
bnd_info = identify_boundaries(geom)
print(f"    bottom (z=0):              {bnd_info['bottom']}")
print(f"    top (z=H):                 {bnd_info['top']}")
print(f"    patch_footprint_interface: {bnd_info['patch_footprint_interface']}")
print(f"    al2_air_rest_interface:    {bnd_info['al2_air_rest_interface']}")
print(f"    all z=dp boundaries:       {bnd_info['z_dp_all']}")

# Print all boundaries for debugging
print("\n    All boundaries:")
for b in bnd_info["all"]:
    if "error" in b:
        print(f"      bnd {b['num']}: ERROR {b['error']}")
    else:
        print(f"      bnd {b['num']}: up={b['up']}, down={b['down']}, normal=({b['normal'][0]:.1f},{b['normal'][1]:.1f},{b['normal'][2]:.1f}), center=({b['center'][0]:.3e},{b['center'][1]:.3e},{b['center'][2]:.3e})")

# --- Update physics: LayeredTransition BC ---
print("\n[8] Updating LayeredTransition BC to patch footprint interface...")
phys = comp.physics()
# Find ewfd
ewfd_tag = None
for t in list(phys.tags()):
    p = phys.get(t)
    if p.label() == "电磁波，频域" or t == "ewfd":
        ewfd_tag = t
        break
if not ewfd_tag:
    # try by scanning
    for t in list(phys.tags()):
        p = phys.get(t)
        try:
            lbl = p.label()
            if "电磁波" in lbl or "ewfd" in lbl.lower():
                ewfd_tag = t
                break
        except:
            pass
print(f"    ewfd tag: {ewfd_tag}")
ewfd = phys.get(ewfd_tag)

# Find LayeredTransition feature
ltr_tag = None
for t in list(ewfd.feature().tags()):
    f = ewfd.feature().get(t)
    try:
        ftype = f.label()
        if "多层过渡" in ftype or "LayeredTransition" in t:
            ltr_tag = t
            break
    except:
        pass
print(f"    LayeredTransition tag: {ltr_tag}")

if ltr_tag and bnd_info["patch_footprint_interface"]:
    ltr = ewfd.feature().get(ltr_tag)
    # Update selection to patch footprint interface
    pf_bnds = bnd_info["patch_footprint_interface"]
    print(f"    Setting LayeredTransition selection to: {pf_bnds}")
    try:
        ltr.selection().set(pf_bnds)
        print("    OK")
    except Exception as e:
        print(f"    ERROR setting selection: {e}")
else:
    print("    WARNING: Could not update LayeredTransition BC!")

# --- Find and check LayeredImpedance BC (bottom) ---
print("\n[9] Checking LayeredImpedance BC (bottom)...")
liz_tag = None
for t in list(ewfd.feature().tags()):
    f = ewfd.feature().get(t)
    try:
        ftype = f.label()
        if "多层阻抗" in ftype or "LayeredImpedance" in t:
            liz_tag = t
            break
    except:
        pass
print(f"    LayeredImpedance tag: {liz_tag}")
if liz_tag:
    liz = ewfd.feature().get(liz_tag)
    try:
        sel = list(liz.selection().entities())
        print(f"    Current selection: {sel}")
        # Should be on bottom (z=0)
        if bnd_info["bottom"]:
            print(f"    Expected bottom: {bnd_info['bottom']}")
            if sel != bnd_info["bottom"]:
                print(f"    Updating to bottom: {bnd_info['bottom']}")
                liz.selection().set(bnd_info["bottom"])
    except Exception as e:
        print(f"    Error: {e}")

# --- Assign air material to patch domain (dom 3) ---
print("\n[10] Assigning air material to patch domain (dom 3)...")
mat_list = comp.material()
# Find existing air material (by tag or by checking relpermittivity≈1)
air_mat_tag = None
for t in list(mat_list.tags()):
    mat = mat_list.get(t)
    try:
        lbl = str(mat.label())
        # Check if this material has relpermittivity ≈ 1 (air)
        try:
            epsr = str(mat.propertyGroup("def").getString("relpermittivity"))
            print(f"    material {t}: label={lbl}, relpermittivity={epsr}")
            if "1" in epsr and t not in ("lml_au",) and "lml" not in t:
                air_mat_tag = t
        except:
            print(f"    material {t}: label={lbl} (no relpermittivity)")
    except:
        pass

if air_mat_tag:
    air_mat = mat_list.get(air_mat_tag)
    try:
        # Get current selection and add dom 3
        cur_sel = list(air_mat.selection().entities())
        print(f"    air material ({air_mat_tag}) current selection: {cur_sel}")
        if 3 not in cur_sel:
            air_mat.selection().set(cur_sel + [3])
            print(f"    Added dom 3 -> selection: {cur_sel + [3]}")
        else:
            print(f"    dom 3 already in selection")
    except Exception as e:
        print(f"    Error adding dom 3: {e}")
        try:
            air_mat.selection().set([2, 3])
            print(f"    Set selection to [2, 3]")
        except Exception as e2:
            print(f"    Error setting selection: {e2}")
else:
    print("    WARNING: Could not find air material! Creating new one...")
    try:
        air_mat = mat_list.create("mat_air2", "Common")
        air_mat.propertyGroup("def").set("relpermittivity", "1")
        air_mat.selection().set([3])
        print("    Created new air material for dom 3")
    except Exception as e:
        print(f"    Error creating air material: {e}")

# --- Check PeriodicStructure (ports should auto-update) ---
print("\n[11] Checking PeriodicStructure...")
ps_tag = None
for t in list(ewfd.feature().tags()):
    f = ewfd.feature().get(t)
    try:
        ftype = f.label()
        if "周期性结构" in ftype or "PeriodicStructure" in t:
            ps_tag = t
            break
    except:
        pass
print(f"    PeriodicStructure tag: {ps_tag}")
if ps_tag:
    ps = ewfd.feature().get(ps_tag)
    # Check excitedPortSelection
    try:
        eps = list(ps.selection("excitedPortSelection").entities())
        print(f"    excitedPortSelection: {eps}")
        if bnd_info["top"]:
            print(f"    Expected top: {bnd_info['top']}")
            if eps != bnd_info["top"]:
                print(f"    Updating excitedPortSelection to top: {bnd_info['top']}")
                ps.selection("excitedPortSelection").set(bnd_info["top"])
    except Exception as e:
        print(f"    Error: {e}")

# --- Rebuild mesh: delete old Sweep, create FreeTet ---
print("\n[12] Rebuilding mesh...")
mesh_list = comp.mesh()
mesh_tags = list(mesh_list.tags())
print(f"    mesh tags: {mesh_tags}")

# Delete old mesh sequences and create a fresh FreeTet
for mt in mesh_tags:
    try:
        mesh_list.remove(mt)
        print(f"    removed mesh {mt}")
    except Exception as e:
        print(f"    could not remove mesh {mt}: {e}")

# Create new Sweep mesh (ensures conforming periodic side faces)
try:
    mesh = mesh_list.create("mesh1")
    # FreeTri on bottom face (z=0, bnd 3) as sweep source
    ftri = mesh.feature().create("ftri1", "FreeTri")
    ftri.selection().set([3])
    # Sweep through all domains (bottom -> top)
    sw = mesh.feature().create("sw1", "Sweep")
    try:
        sw.selection("source").set([3])   # bottom face
    except Exception:
        print("    (sweep source auto-detected)")
    mesh.run()
    print(f"    Sweep mesh built: {mesh.getNumElem()} elements, {mesh.getNumVertex()} vertices")
except Exception as e:
    print(f"    Sweep mesh error: {e}")
    # Fallback: FreeTet with boundary mesh on sides
    try:
        mesh = mesh_list.create("mesh1")
        # Map the 4 side faces for periodic conformity
        # sides: bnd 1(-x), 16(+x), 2(-y), 8(+y) for dom1; bnd 4(-x), 17(+x), 5(-y), 9(+y) for dom2
        # Actually, identify side pairs by normal and coordinate
        side_bnds = []
        for b in bnd_info["all"]:
            if "normal" in b and "center" in b:
                nx, ny, nz = b["normal"]
                cx, cy, cz = b["center"]
                if abs(nz) < 0.5:  # vertical face (side)
                    side_bnds.append(b["num"])
        print(f"    Side boundaries for mapping: {side_bnds}")
        
        # FreeTet for volume (will need conforming sides)
        ft = mesh.feature().create("freet1", "FreeTet")
        mesh.run()
        print(f"    FreeTet fallback mesh built: {mesh.getNumElem()} elements")
        print("    WARNING: Floquet periodicity may fail with non-conforming side mesh!")
    except Exception as e2:
        print(f"    Fallback mesh error: {e2}")

# --- Solve ---
print("\n[13] Solving...")
study_list = mj.study()
study_tags = list(study_list.tags())
print(f"    study tags: {study_tags}")
for st in study_tags:
    print(f"    study {st}: {study_list.get(st).label()}")

try:
    mj.study(study_tags[0]).run()
    print("    Solve completed!")
except Exception as e:
    print(f"    Solve error: {e}")
    print("    Trying to get more info...")
    import traceback
    traceback.print_exc()

# --- Evaluate ---
print("\n[14] Evaluating Rtotal vs wl...")
try:
    # Get inner solution values (wl sweep)
    sol_tags = list(mj.sol().tags())
    print(f"    solution tags: {sol_tags}")
    if sol_tags:
        sol = mj.sol(sol_tags[0])
        # Try evaluating
        try:
            results = m.evaluate(["ewfd.Rtotal", "wl"])
            print(f"    Results shape: {len(results) if hasattr(results, '__len__') else 'scalar'}")
            if hasattr(results, '__len__') and len(results) > 0:
                for row in results:
                    if hasattr(row, '__len__'):
                        print(f"      wl={row[1]:.2e}  R={row[0]:.6f}")
                    else:
                        print(f"      {row}")
            else:
                print(f"    Rtotal = {results}")
        except Exception as e:
            print(f"    evaluate error: {e}")
            # Try single expression
            try:
                r = m.evaluate("ewfd.Rtotal")
                print(f"    Rtotal (all) = {r}")
            except Exception as e2:
                print(f"    single evaluate error: {e2}")
except Exception as e:
    print(f"    Evaluation error: {e}")

# --- Save ---
print("\n[15] Saving model...")
try:
    m.save(OUT_PATH)
    print(f"    Saved to {OUT_PATH}")
except Exception as e:
    print(f"    Save error: {e}")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)

try:
    client.disconnect()
except Exception:
    pass
