"""Probe baseline model's mesh sequence to understand Sweep setup."""
import mph

MODEL = r"C:\Users\陆星\Desktop\MIM_paper_baseline_v1.mph"

client = mph.Client(cores=4)
m = client.load(MODEL)
mj = m.java
comp = mj.component("comp1")

mesh_list = comp.mesh()
for t in list(mesh_list.tags()):
    mesh = mesh_list.get(t)
    print(f"\n=== mesh {t}: label={mesh.label()} ===")
    print(f"  feature().size() = {mesh.feature().size()}")
    for ft in list(mesh.feature().tags()):
        f = mesh.feature().get(ft)
        print(f"  feature {ft}:")
        try:
            print(f"    label = {f.label()}")
        except:
            pass
        try:
            ftype = f.getString("type")
            print(f"    type = {ftype}")
        except:
            pass
        # Try to get all properties
        try:
            props = list(f.properties())
            print(f"    properties = {props}")
        except:
            pass
        # Try to get selection info
        try:
            for sel_name in ["selection", "source", "target", "domains", "bound"]:
                try:
                    sel = f.selection(sel_name)
                    ents = list(sel.entities())
                    print(f"    {sel_name} = {ents}")
                except:
                    pass
        except:
            pass
        # Try geom selection
        try:
            sels = list(f.selections())
            for sn in sels:
                try:
                    ents = list(f.selection(sn).entities())
                    print(f"    sel[{sn}] = {ents}")
                except:
                    pass
        except:
            pass

try:
    client.disconnect()
except:
    pass
