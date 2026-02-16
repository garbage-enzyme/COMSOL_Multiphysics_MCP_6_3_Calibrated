"""Simple test to add physics using mph library."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph

print("Starting COMSOL...")
client = mph.start(cores=4)

# Create new model with proper setup
print("Creating new model...")
model = client.create('test2')
jm = model.java

# Add parameters
params = jm.param()
params.set('w_ch', '100[um]')
params.set('h_ch', '50[um]')
params.set('L_ch', '500[um]')
params.set('v_in', '1[mm/s]')
print("Parameters added")

# Create component
print("Creating 3D component...")
comp = jm.component().create('comp1', True)

# Create 3D geometry
print("Creating 3D geometry...")
geom = comp.geom().create('geom1', 3)

# Add a simple block
blk = geom.feature().create('blk1', 'Block')
blk.set('size', ['L_ch', 'w_ch', 'h_ch'])
blk.set('pos', ['0', '0', '0'])

# Build geometry
print("Building geometry...")
geom.run()
print("Geometry built")

# Add water material
print("Adding water material...")
mat = comp.material().create('mat1', 'Common')
mat.propertyGroup('def').set('relpermeability', '1')
mat.propertyGroup('def').set('relpermittivity', '80')
mat.propertyGroup('def').set('density', '1000[kg/m^3]')
mat.propertyGroup('def').set('dynamicviscosity', '0.001[Pa*s]')
mat.label('Water')
print("Water material added")

# Now add Laminar Flow physics (need to pass geometry tag!)
print("Adding Laminar Flow physics...")
spf = comp.physics().create('spf', 'LaminarFlow', 'geom1')
print(f"Physics created: {spf.tag()}")

# Add mesh
print("Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)  # Finer mesh
mesh.run()
print("Mesh created")

# Add study
print("Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("Solving...")
study.run()
print("Solution complete!")

# Save
model.save('test_simple.mph')
print("Model saved as test_simple.mph")

client.clear()
print("Done!")
