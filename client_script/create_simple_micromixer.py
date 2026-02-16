"""Create simplified micromixer model using mph library."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph

print("=" * 60)
print("Micromixer Simulation - Simplified T-shaped Mixer")
print("=" * 60)

print("\n[1] Starting COMSOL client...")
client = mph.start(cores=4)
print("    Client started with 4 cores")

print("\n[2] Creating model...")
model = client.create('micromixer_simple')
jm = model.java

# Parameters
print("\n[3] Setting parameters...")
params = jm.param()
params.set('w_ch', '100[um]')
params.set('h_ch', '50[um]')
params.set('L_in', '300[um]')
params.set('L_out', '600[um]')
params.set('v_in', '1[mm/s]')

# Create component and geometry
print("\n[4] Creating 3D component and geometry...")
comp = jm.component().create('comp1', True)
geom = comp.geom().create('geom1', 3)

# Create simple channel geometry (single block)
blk = geom.feature().create('blk1', 'Block')
blk.set('base', 'center')
blk.set('size', ['L_out', 'w_ch', 'h_ch'])
blk.set('pos', ['0', '0', 'h_ch/2'])

print("    Building geometry...")
geom.run()
print("    Geometry built: Simple channel")

# Add water material
print("\n[5] Adding water material...")
mat = comp.material().create('mat1', 'Common')
mat.propertyGroup('def').set('relpermeability', '1')
mat.propertyGroup('def').set('relpermittivity', '80')
mat.propertyGroup('def').set('density', '1000[kg/m^3]')
mat.propertyGroup('def').set('dynamicviscosity', '0.001[Pa*s]')
mat.label('Water')

# Add Laminar Flow physics
print("\n[6] Adding Laminar Flow physics...")
spf = comp.physics().create('spf', 'LaminarFlow', 'geom1')

# Create mesh
print("\n[7] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)
mesh.run()
print("    Mesh generated")

# Add study and solve
print("\n[8] Adding stationary study and solving...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

print("    Solving (this may take a moment)...")
study.run()
print("    Solution complete!")

# Save
print("\n[9] Saving model...")
model.save('micromixer_simple.mph')
print("    Model saved as micromixer_simple.mph")

print("\n" + "=" * 60)
print("Simulation completed successfully!")
print("Note: Default boundary conditions applied (no-slip walls)")
print("=" * 60)

client.clear()
