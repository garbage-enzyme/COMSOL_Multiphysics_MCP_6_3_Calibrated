"""Complete micromixer simulation setup using mph library."""
import sys
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph

print("Starting COMSOL client...")
client = mph.start(cores=4)
print("Client started")

# Load existing model
print("\nLoading micromixer model...")
model = client.load('micromixer.mph')
print(f"Model: {model.name()}")

# Get Java model
jm = model.java
comp = jm.component('comp1')
geom = comp.geom('geom1')

# Rebuild geometry to ensure it's ready
print("\nRebuilding geometry...")
geom.run()
print("Geometry rebuilt")

# Add water material
print("\nAdding water material...")
mat = comp.material().create('mat1', 'Common')
mat.propertyGroup('def').set('relpermeability', '1')
mat.propertyGroup('def').set('relpermittivity', '80')
mat.propertyGroup('def').set('density', '1000[kg/m^3]')
mat.propertyGroup('def').set('dynamicviscosity', '0.001[Pa*s]')
mat.label('Water')
print("Water material added")

# Add Laminar Flow physics
print("\nAdding Laminar Flow physics...")
spf = comp.physics().create('spf', 'LaminarFlow')
spf.label('Laminar Flow')
print("Laminar Flow physics added")

# Add Transport of Diluted Species for mixing visualization
print("\nAdding Transport of Diluted Species physics...")
tds = comp.physics().create('tds', 'DilutedSpecies')
tds.label('Transport of Diluted Species')
print("Transport physics added")

# Get geometry info for boundary selections
print("\nGetting geometry boundaries...")
geom.run()
info = geom.info()
print(f"  Domains: {info.ndomain}")
print(f"  Boundaries: {info.nboundary}")

# Add inlet 1 velocity boundary condition
print("\nAdding boundary conditions...")
inlet1 = spf.create('inl1', 'InletBoundary')
inlet1.label('Inlet 1')
inlet1.set('U0', ['0', '0', 'v_inlet'])
print("  Added inlet 1 (velocity)")

# Add inlet 2 velocity boundary condition
inlet2 = spf.create('inl2', 'InletBoundary')
inlet2.label('Inlet 2')
inlet2.set('U0', ['0', '0', 'v_inlet'])
print("  Added inlet 2 (velocity)")

# Add outlet boundary condition
outlet = spf.create('out1', 'OutletBoundary')
outlet.label('Outlet')
outlet.set('p0', '0')
print("  Added outlet (pressure)")

# Add concentration at inlet 1
c_inlet1 = tds.create('cin1', 'Concentration')
c_inlet1.label('Inlet 1 Concentration')
c_inlet1.set('c0', '1')
print("  Added concentration inlet 1 (c=1)")

# Add concentration at inlet 2
c_inlet2 = tds.create('cin2', 'Concentration')
c_inlet2.label('Inlet 2 Concentration')
c_inlet2.set('c0', '0')
print("  Added concentration inlet 2 (c=0)")

# Add mesh
print("\nCreating mesh...")
mesh = comp.mesh().create('mesh1', geom)
mesh.feature().create('ftr1', 'FreeTet')
mesh.run()
print("Mesh created")

# Get mesh statistics
print(f"  Mesh elements: {mesh.info().nelems}")

# Add study
print("\nAdding study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')
print("Stationary study added")

# Solve
print("\nSolving...")
jm.solve('std1')
print("Solution completed")

# Save model
print("\nSaving model...")
model.save('micromixer_solved.mph')
print("Model saved as micromixer_solved.mph")

# Cleanup
client.clear()
print("\nDone!")
