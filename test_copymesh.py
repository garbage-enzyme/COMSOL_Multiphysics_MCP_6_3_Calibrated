"""Find correct mesh feature type for Copy Mesh / Identical Mesh, then build
FreeTet + CopyMesh mesh for 3-domain patch model with periodic conditions.

Tries: CopyFace, CopyMesh, IdenticalMesh, Copy, etc.
"""
import mph
import jpype as _jpp

MODEL = r"C:\Users\陆星\Desktop\MIM_patch_v1.mph"  # 3-dom short patch, FormUnion

# Paper parameters
P = 1.35e-6
L = 8.56e-7

client = mph.Client(cores=4)
m = client.load(MODEL)
mj = m.java
comp = mj.component("comp1")
geom = comp.geom("geom1")

# Identify side face boundaries (from previous probe)
# x=0: bnd 1 (Al2O3, dom1), bnd 4 (air, dom2)
# x=P: bnd 16 (Al2O3, dom1), bnd 17 (air, dom2)
# y=0: bnd 2 (Al2O3, dom1), bnd 5 (air, dom2)
# y=P: bnd 8 (Al2O3, dom1), bnd 9 (air, dom2)
x_src = [1, 4]   # x=0
x_dst = [16, 17]  # x=P
y_src = [2, 5]   # y=0
y_dst = [8, 9]   # y=P

# Delete old mesh
mesh_list = comp.mesh()
for mt in list(mesh_list.tags()):
    mesh_list.remove(mt)
    print(f"Removed mesh {mt}")

# Create new mesh sequence
mesh = mesh_list.create("mesh1")

# Try to find the Copy Mesh / Identical Mesh feature type
# by trying to create features with different type names
copy_type = None
for tname in ["CopyFace", "CopyMesh", "IdenticalMesh", "Copy", "Identical"]:
    try:
        feat = mesh.feature().create("test1", tname)
        print(f"SUCCESS: feature type '{tname}' works!")
        copy_type = tname
        # Remove test feature
        mesh.feature().remove("test1")
        break
    except Exception as e:
        print(f"FAIL: '{tname}': {str(e)[:60]}")

if copy_type is None:
    # Try JPype reflection to list all mesh feature types
    print("\nTrying to enumerate mesh feature types via reflection...")
    try:
        ms_class = mesh.getClass()
        for meth in ms_class.getMethods():
            mname = str(meth.getName())
            if "create" in mname.lower():
                print(f"  method: {mname}, params: {[str(p.getName()) for p in meth.getParameterTypes()]}")
    except Exception as e:
        print(f"  Reflection error: {e}")

    # Try physics-controlled mesh
    print("\nTrying physics-controlled mesh...")
    mesh_list.remove("mesh1")
    mesh = mesh_list.create("mesh1")
    # Try setting physics-controlled property
    for prop in ["physics-controlled", "physicscontrolled", "auto", "type"]:
        try:
            mesh.set(prop, True)
            print(f"  set('{prop}', True) worked")
        except:
            try:
                mesh.set(prop, "physics")
                print(f"  set('{prop}', 'physics') worked")
            except:
                pass
    try:
        mesh.run()
        print(f"  Physics-controlled mesh built: {mesh.getNumElem()} elements")
    except Exception as e:
        print(f"  Physics-controlled mesh failed: {e}")
        # Just try FreeTet
        mesh_list.remove("mesh1")
        mesh = mesh_list.create("mesh1")
        ft = mesh.feature().create("ft1", "FreeTet")
        mesh.run()
        print(f"  FreeTet mesh built: {mesh.getNumElem()} elements")

else:
    # Build: FreeTri on source faces + CopyMesh + FreeTet
    print(f"\nBuilding mesh with {copy_type}...")

    # 1. FreeTri on source side faces
    ftri_x = mesh.feature().create("ftri_x", "FreeTri")
    ftri_x.selection().set(x_src)
    print(f"  FreeTri on x=0 faces: {x_src}")

    ftri_y = mesh.feature().create("ftri_y", "FreeTri")
    ftri_y.selection().set(y_src)
    print(f"  FreeTri on y=0 faces: {y_src}")

    # 2. CopyMesh from source to destination
    cp_x = mesh.feature().create("cp_x", copy_type)
    try:
        cp_x.selection("source").set(x_src)
        cp_x.selection("destination").set(x_dst)
    except:
        try:
            cp_x.selection("src").set(x_src)
            cp_x.selection("dst").set(x_dst)
        except:
            try:
                cp_x.selection().set(x_src + x_dst)
            except:
                pass
    print(f"  {copy_type} x: {x_src} -> {x_dst}")

    cp_y = mesh.feature().create("cp_y", copy_type)
    try:
        cp_y.selection("source").set(y_src)
        cp_y.selection("destination").set(y_dst)
    except:
        try:
            cp_y.selection("src").set(y_src)
            cp_y.selection("dst").set(y_dst)
        except:
            try:
                cp_y.selection().set(y_src + y_dst)
            except:
                pass
    print(f"  {copy_type} y: {y_src} -> {y_dst}")

    # 3. FreeTet for volume
    ft = mesh.feature().create("ft1", "FreeTet")
    print(f"  FreeTet for volume")

    # Build mesh
    try:
        mesh.run()
        print(f"\n  Mesh built: {mesh.getNumElem()} elements, {mesh.getNumVertex()} vertices")
    except Exception as e:
        print(f"\n  Mesh build failed: {e}")
        # Try without FreeTri (just FreeTet + CopyMesh)
        print("  Trying without FreeTri...")
        for ft_name in ["ftri_x", "ftri_y"]:
            try:
                mesh.feature().remove(ft_name)
            except:
                pass
        try:
            mesh.run()
            print(f"  Mesh built: {mesh.getNumElem()} elements")
        except Exception as e2:
            print(f"  Still failed: {e2}")

# Solve
print("\nSolving...")
try:
    mj.study("std1").run()
    print("  Solve completed!")
except Exception as e:
    print(f"  Solve error: {str(e)[:200]}")

# Evaluate
print("\nEvaluating Rtotal vs wl...")
try:
    results = m.evaluate(["ewfd.Rtotal", "wl"])
    for row in results:
        wl_um = float(row[1]) * 1e6
        r = float(row[0])
        emissivity = 1 - r
        print(f"  wl={wl_um:.2f}um  R={r:.6f}  eps={emissivity:.6f}")
except Exception as e:
    print(f"  Evaluate error: {e}")

# Save
m.save(r"C:\Users\陆星\Desktop\MIM_patch_copymesh.mph")
print("\nSaved.")
try:
    client.disconnect()
except:
    pass
