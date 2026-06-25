import mph
import numpy as np

client = mph.start(cores=6)

path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC_N300_freq.mph'
model = client.load(path)
jmodel = model.java
comp1 = jmodel.component('comp1')
geom = comp1.geom('geom1')

# Build mesh
mesh = comp1.mesh()
if 'mesh1' in list(mesh.tags()):
    mesh.remove('mesh1')
mesh.create('mesh1')
mesh.run()
print('Mesh built')

# Identify each boundary by evaluating a point on it
print('\n=== Boundary Identification ===')
for bnd in range(1, geom.getNBoundaries() + 1):
    # Use a CutPoint2D at the approximate center of each boundary
    # We know the geometry: these are the approximate boundary centers
    pass
