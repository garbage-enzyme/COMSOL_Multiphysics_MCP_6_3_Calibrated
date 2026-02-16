"""Test micromixer model creation using mph library."""
import sys
import os

# Ensure UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph

print("Starting COMSOL client...")
client = mph.start(cores=4)
print("Client started")

# Create model
print("\nCreating micromixer model...")
model = client.create('micromixer')
print(f"Model: {model.name()}")

# Get Java model for low-level access
jm = model.java
print(f"Java model type: {type(jm).__name__}")

# Create component
print("\nCreating 3D component...")
comp = jm.component().create('comp1', True)
print(f"Component: {comp.tag()}")

# Create 3D geometry
print("\nCreating 3D geometry...")
geom = comp.geom().create('geom1', 3)
print(f"Geometry: {geom.tag()}")

# Add parameters
print("\nAdding parameters...")
params = jm.param()
params.set('w_channel', '100[um]')
params.set('h_channel', '50[um]')
params.set('L_inlet', '300[um]')
params.set('L_outlet', '600[um]')
params.set('v_inlet', '1[mm/s]')
print("Parameters added")

# Create T-mixer geometry using blocks
print("\nCreating T-mixer geometry...")

# Inlet 1 (left)
blk1 = geom.feature().create('blk1', 'Block')
blk1.set('base', 'center')
blk1.set('size', ['L_inlet', 'w_channel', 'h_channel'])
blk1.set('pos', ['-L_inlet/2', '-w_channel/2', '0'])
print("  Added inlet 1 block")

# Inlet 2 (right)
blk2 = geom.feature().create('blk2', 'Block')
blk2.set('base', 'center')
blk2.set('size', ['L_inlet', 'w_channel', 'h_channel'])
blk2.set('pos', ['-L_inlet/2', 'w_channel/2', '0'])
print("  Added inlet 2 block")

# Mixing channel (main)
blk3 = geom.feature().create('blk3', 'Block')
blk3.set('base', 'center')
blk3.set('size', ['w_channel', '3*w_channel', 'h_channel'])
blk3.set('pos', ['w_channel/2', '0', '0'])
print("  Added mixing channel block")

# Outlet
blk4 = geom.feature().create('blk4', 'Block')
blk4.set('base', 'center')
blk4.set('size', ['L_outlet', 'w_channel', 'h_channel'])
blk4.set('pos', ['w_channel/2 + L_outlet/2', '0', '0'])
print("  Added outlet block")

# Union all blocks
union = geom.feature().create('uni1', 'Union')
union.selection('input').set(['blk1', 'blk2', 'blk3', 'blk4'])
print("  Created union of all blocks")

# Build geometry
print("\nBuilding geometry...")
geom.run()
print("Geometry built successfully")

# Check geometry info
print(f"\nGeometries in model: {model.geometries()}")

# Save model
print("\nSaving model...")
model.save('micromixer.mph')
print("Model saved as micromixer.mph")

# Cleanup
client.clear()
print("\nDone!")
