"""Build EC-NDT COMSOL model using MPh."""
import mph
import numpy as np

client = mph.Client(cores=4)

model = client.create("EC_NDT_Model")

# Parameters
model.parameter("len_unit", "1[mm]")
model.description("len_unit", "Length unit: mm")

# Use MPh Node API for everything
# Create 2D geometry via model.java
jmodel = model.java
geom1 = jmodel.geom().create("geom1", 2)
geom1.label("Geometry 1")

# Build rectangles using MPh Node API
# Access geometry through MPh Node
geom_node = model / "geometries" / "Geometry 1"

# Air domain: 80x80 mm centered at (0,0)
r1 = geom_node.create("Rectangle")
r1.property("size", [80, 80])
r1.property("pos", [-40, -40])
r1.property("base", "center")

# Right coil coil+: 2x10 mm centered at (6,0)
r2 = geom_node.create("Rectangle", name="r2")
r2.property("size", [2, 10])
r2.property("pos", [6, 0])
r2.property("base", "center")

# Left coil coil-: 2x10 mm centered at (-6,0)
r3 = geom_node.create("Rectangle")
r3.property("size", [2, 10])
r3.property("pos", [-6, 0])
r3.property("base", "center")

# Steel specimen: 40x2 mm centered at (0,-7)
r4 = geom_node.create("Rectangle")
r4.property("size", [40, 2])
r4.property("pos", [0, -7])
r4.property("base", "center")

geom_node.run()
print("Geometry built successfully")

# Materials
mat_air = jmodel.material().create("mat1", "Basic")
mat_air.label("Air")
mat_air.selection().set([1])
mat_air.propertyGroup("def").set("relpermeability", "1")
mat_air.propertyGroup("def").set("electricconductivity", "0[S/m]")

mat_steel = jmodel.material().create("mat2", "Basic")
mat_steel.label("Steel specimen")
mat_steel.selection().set([2])
mat_steel.propertyGroup("def").set("relpermeability", "100")
mat_steel.propertyGroup("def").set("electricconductivity", "6.99e6[S/m]")

mat_copper = jmodel.material().create("mat3", "Basic")
mat_copper.label("Copper")
mat_copper.selection().set([3, 4])
mat_copper.propertyGroup("def").set("relpermeability", "1")
mat_copper.propertyGroup("def").set("electricconductivity", "6e7[S/m]")
print("Materials created")

# Physics: Magnetic Fields
physics = jmodel.physics().create("mf", "MagneticFields")
physics.label("Magnetic Fields")
print("Magnetic Fields physics added")

# Coil 1 (right coil, coil+): domain 4
coil1 = physics.create("coil1", "Coil")
coil1.selection().set([4])
coil1.set("CoilType", "Multi-turn")
coil1.set("Icoil", "1[A]")
coil1.set("N", "300")
coil1.label("Coil 1 (Right)")

# Coil 2 (left coil, coil-): domain 3
coil2 = physics.create("coil2", "Coil")
coil2.selection().set([3])
coil2.set("CoilType", "Multi-turn")
coil2.set("Icoil", "-1[A]")
coil2.set("N", "300")
coil2.label("Coil 2 (Left)")
print("Coils configured")

# Study
study = jmodel.study().create("std1")
study.label("Study 1")

# Step 1: Coil Geometry Analysis
step1 = study.create("step1", "CoilGeometryAnalysis")
step1.label("Coil Geometry Analysis")

# Step 2: Stationary
step2 = study.create("step2", "Stationary")
step2.label("Stationary")
print("Study created")

# Mesh
mesh1 = jmodel.mesh().create("mesh1")
# Use fine mesh
mesh1.autoMeshSize(4)
mesh1.run()
print("Mesh generated")

# Solve
jmodel.study("std1").run()
print("Study solved")

# Evaluate
B_norm = model.evaluate("mf.normB", "T")
print(f"B_norm type: {type(B_norm)}, value: {B_norm}")
B_array = np.atleast_1d(np.array(B_norm, dtype=float))
B_max = float(np.max(B_array))
B_mean = float(np.mean(B_array))
print(f"Bmax = {B_max:.10f} T")
print(f"Bmax = {B_max*1000:.3f} mT")
print(f"Mean |B| = {B_mean*1000:.3f} mT")

model.save(r"C:\Users\nguye\EC_NDT_Model.mph")
print("Model saved to C:\\Users\\nguye\\EC_NDT_Model.mph")
