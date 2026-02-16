"""Create and solve micromixer model using mph library."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph

print("=" * 60)
print("Micromixer Simulation - T-shaped Microfluidic Mixer")
print("=" * 60)

print("\n[1] Starting COMSOL client...")
client = mph.start(cores=4)
print("    Client started with 4 cores")

print("\n[2] Creating model...")
model = client.create('micromixer_v2')
jm = model.java

# Parameters
print("\n[3] Setting parameters...")
params = jm.param()
params.set('w_ch', '100[um]')      # Channel width
params.set('h_ch', '50[um]')       # Channel height
params.set('L_in', '300[um]')      # Inlet length
params.set('L_out', '600[um]')     # Outlet length
params.set('v_in', '1[mm/s]')      # Inlet velocity
params.set('D_c', '1e-9[m^2/s]')   # Diffusion coefficient
print("    w_ch=100um, h_ch=50um, L_in=300um, L_out=600um, v_in=1mm/s")

# Create component
print("\n[4] Creating 3D component...")
comp = jm.component().create('comp1', True)

# Create 3D geometry
print("\n[5] Creating T-mixer geometry...")
geom = comp.geom().create('geom1', 3)

# Inlet 1 (left side, y-)
blk1 = geom.feature().create('blk1', 'Block')
blk1.set('base', 'center')
blk1.set('size', ['L_in', 'w_ch', 'h_ch'])
blk1.set('pos', ['-L_in/2', '-w_ch', 'h_ch/2'])
blk1.label('Inlet 1')

# Inlet 2 (left side, y+)
blk2 = geom.feature().create('blk2', 'Block')
blk2.set('base', 'center')
blk2.set('size', ['L_in', 'w_ch', 'h_ch'])
blk2.set('pos', ['-L_in/2', 'w_ch', 'h_ch/2'])
blk2.label('Inlet 2')

# Mixing channel (center)
blk3 = geom.feature().create('blk3', 'Block')
blk3.set('base', 'center')
blk3.set('size', ['w_ch', '3*w_ch', 'h_ch'])
blk3.set('pos', ['w_ch/2', '0', 'h_ch/2'])
blk3.label('Mixing Channel')

# Outlet (right side)
blk4 = geom.feature().create('blk4', 'Block')
blk4.set('base', 'center')
blk4.set('size', ['L_out', 'w_ch', 'h_ch'])
blk4.set('pos', ['w_ch/2 + L_out/2', '0', 'h_ch/2'])
blk4.label('Outlet')

# Union all blocks
union = geom.feature().create('uni1', 'Union')
union.selection('input').set(['blk1', 'blk2', 'blk3', 'blk4'])
union.label('T-Mixer')

print("    Building geometry...")
geom.run()
print("    Geometry built: T-shaped mixer with 2 inlets, 1 outlet")

# Add water material
print("\n[6] Adding water material...")
mat = comp.material().create('mat1', 'Common')
mat.propertyGroup('def').set('relpermeability', '1')
mat.propertyGroup('def').set('relpermittivity', '80')
mat.propertyGroup('def').set('density', '1000[kg/m^3]')
mat.propertyGroup('def').set('dynamicviscosity', '0.001[Pa*s]')
mat.label('Water')
print("    Water: rho=1000 kg/m3, mu=0.001 Pa*s")

# Add Laminar Flow physics
print("\n[7] Adding Laminar Flow physics (spf)...")
spf = comp.physics().create('spf', 'LaminarFlow', 'geom1')
spf.label('Laminar Flow')

# Add Transport of Diluted Species
print("\n[8] Adding Transport of Diluted Species (tds)...")
tds = comp.physics().create('tds', 'DilutedSpecies', 'geom1')
tds.label('Transport of Diluted Species')
tds.prop('TransportMechanism').set('Convection', True)
tds.feature('cdm1').set('D_c', 'D_c')

# Get boundary info
print("\n[9] Getting boundary information...")
geom.run()

# Add inlet boundary conditions
print("\n[10] Setting boundary conditions...")
# Inlet 1 - normal inflow velocity
inl1 = spf.create('inl1', 'InletBoundary')
inl1.label('Inlet 1 - Flow')
inl1.set('U0', 'v_in')  # Normal inflow velocity

# Inlet 2 - normal inflow velocity
inl2 = spf.create('inl2', 'InletBoundary')
inl2.label('Inlet 2 - Flow')
inl2.set('U0', 'v_in')  # Normal inflow velocity

# Outlet - pressure
out1 = spf.create('out1', 'OutletBoundary')
out1.label('Outlet - Pressure')

# Concentration at inlet 1 (c=1)
cin1 = tds.create('cin1', 'Inflow')
cin1.label('Inlet 1 - Conc (c=1)')
cin1.set('c0_in', '1')

# Concentration at inlet 2 (c=0)
cin2 = tds.create('cin2', 'Inflow')
cin2.label('Inlet 2 - Conc (c=0)')
cin2.set('c0_in', '0')

print("    Inlet 1: v=v_in, c=1")
print("    Inlet 2: v=v_in, c=0")
print("    Outlet: p=0")

# Create mesh
print("\n[11] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)  # Finer mesh
mesh.run()
print("    Mesh generated")

# Add study
print("\n[12] Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("\n[13] Solving...")
print("    This may take a minute...")
study.run()
print("    Solution complete!")

# Save model
print("\n[14] Saving model...")
model.save('micromixer_final.mph')
print("    Model saved as micromixer_final.mph")

print("\n" + "=" * 60)
print("Micromixer simulation completed successfully!")
print("=" * 60)

client.clear()
