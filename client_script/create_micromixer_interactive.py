"""Interactive Micromixer Simulation with Boundary Condition Selection."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path

print("=" * 70)
print("Interactive Micromixer Simulation")
print("=" * 70)

# Model name and directory structure
MODEL_NAME = "micromixer"
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "comsol_models" / MODEL_NAME
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print(f"\nModel directory: {MODELS_DIR}")

# Start COMSOL
print("\n[1] Starting COMSOL...")
client = mph.start(cores=4)
print("    Client started")

# Create model
print("\n[2] Creating model...")
model = client.create(MODEL_NAME)
jm = model.java
print(f"    Model: {model.name()}")

# Add parameters
print("\n[3] Setting parameters...")
params = jm.param()
params.set('w_ch', '100[um]')
params.set('h_ch', '50[um]')
params.set('L_in', '300[um]')
params.set('L_out', '600[um]')
params.set('v_in', '1[mm/s]')
params.set('D_c', '1e-9[m^2/s]')
print("    Parameters added")

# Create component and geometry
print("\n[4] Creating 3D geometry...")
comp = jm.component().create('comp1', True)
geom = comp.geom().create('geom1', 3)

# Create T-mixer geometry
# Inlet 1 (y- side)
blk1 = geom.feature().create('blk1', 'Block')
blk1.set('base', 'center')
blk1.set('size', ['L_in', 'w_ch', 'h_ch'])
blk1.set('pos', ['-L_in/2', '-w_ch', 'h_ch/2'])
blk1.label('Inlet 1')

# Inlet 2 (y+ side)
blk2 = geom.feature().create('blk2', 'Block')
blk2.set('base', 'center')
blk2.set('size', ['L_in', 'w_ch', 'h_ch'])
blk2.set('pos', ['-L_in/2', 'w_ch', 'h_ch/2'])
blk2.label('Inlet 2')

# Mixing channel
blk3 = geom.feature().create('blk3', 'Block')
blk3.set('base', 'center')
blk3.set('size', ['w_ch', '3*w_ch', 'h_ch'])
blk3.set('pos', ['w_ch/2', '0', 'h_ch/2'])
blk3.label('Mixing Channel')

# Outlet
blk4 = geom.feature().create('blk4', 'Block')
blk4.set('base', 'center')
blk4.set('size', ['L_out', 'w_ch', 'h_ch'])
blk4.set('pos', ['w_ch/2 + L_out/2', '0', 'h_ch/2'])
blk4.label('Outlet')

# Union all blocks
union = geom.feature().create('uni1', 'Union')
union.selection('input').set(['blk1', 'blk2', 'blk3', 'blk4'])
union.label('T-Mixer Body')

print("    Building geometry...")
geom.run()
print("    Geometry built")

# Get geometry info
info = geom.info()
print(f"    Domains: {info.ndomain}, Boundaries: {info.nboundary}")

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
spf.label('Laminar Flow')

# Add Transport of Diluted Species
print("\n[7] Adding Transport of Diluted Species...")
tds = comp.physics().create('tds', 'DilutedSpecies', 'geom1')
tds.label('Transport of Diluted Species')
tds.prop('TransportMechanism').set('Convection', True)
tds.feature('cdm1').set('D_c', 'D_c')

# Create mesh
print("\n[8] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)
mesh.run()
print("    Mesh generated")

# Now we need to identify boundaries
print("\n" + "=" * 70)
print("BOUNDARY CONDITION SETUP")
print("=" * 70)

print(f"""
Geometry Information:
  Total boundaries: {info.nboundary}
  Total domains: {info.ndomain}

T-Mixer Structure:
  - Inlet 1: Bottom-left inlet (y- direction)
  - Inlet 2: Top-left inlet (y+ direction)
  - Outlet: Right outlet (x+ direction)
  - Walls: All other surfaces (no-slip)

Typical boundary assignments for a T-mixer:
  - Boundaries at x = -L_in (left face): INLETS
  - Boundaries at x = w_ch + L_out (right face): OUTLET
  - All other boundaries: WALLS (default)
""")

# Interactive boundary selection
print("\nPlease specify boundary numbers for each condition:")
print("(Based on geometry, boundaries are typically numbered by COMSOL)")

# For automated testing, we'll use typical boundary numbers
# In a real interactive session, we'd use input()
try:
    # Try to identify boundaries by position
    # This is geometry-dependent, so we'll use a common pattern
    
    # For T-mixer geometry:
    # - Left inlet faces: typically boundaries at minimum x
    # - Right outlet face: typically boundary at maximum x
    
    # We'll create boundary conditions on specific boundaries
    # These need to be adjusted based on actual boundary numbering
    
    print("\nAttempting to auto-detect boundaries...")
    
    # Since boundary detection is complex, we'll ask the user
    print("""
To identify correct boundary numbers:
1. In COMSOL GUI, open the model and check Selection List
2. Click on each face to see its boundary number
3. Note: Inlet 1 (bottom), Inlet 2 (top), Outlet (right)

For this demo, we'll use boundary-based selection by position.
    """)
    
    # Ask user for boundary numbers
    inlet1_input = input("Enter boundary number(s) for Inlet 1 (comma-separated): ").strip()
    inlet2_input = input("Enter boundary number(s) for Inlet 2 (comma-separated): ").strip()
    outlet_input = input("Enter boundary number(s) for Outlet (comma-separated): ").strip()
    
    inlet1_boundaries = [int(b.strip()) for b in inlet1_input.split(',') if b.strip()]
    inlet2_boundaries = [int(b.strip()) for b in inlet2_input.split(',') if b.strip()]
    outlet_boundaries = [int(b.strip()) for b in outlet_input.split(',') if b.strip()]
    
    print(f"\nSelected boundaries:")
    print(f"  Inlet 1: {inlet1_boundaries}")
    print(f"  Inlet 2: {inlet2_boundaries}")
    print(f"  Outlet: {outlet_boundaries}")
    
except EOFError:
    # Non-interactive mode, use defaults
    print("\nNon-interactive mode - skipping boundary setup")
    print("You can manually set boundaries in COMSOL GUI")
    inlet1_boundaries = []
    inlet2_boundaries = []
    outlet_boundaries = []

# Add boundary conditions
print("\n[9] Configuring boundary conditions...")
bc_results = {"inlets": [], "outlets": []}

# Inlet 1
for i, bnd in enumerate(inlet1_boundaries):
    inlet1 = spf.create(f'inl1_{i}', 'InletBoundary')
    inlet1.selection().set([bnd])
    inlet1.set('U0', 'v_in')
    inlet1.label(f'Inlet 1 - Boundary {bnd}')
    
    # Concentration = 1 at inlet 1
    cin1 = tds.create(f'cin1_{i}', 'Inflow')
    cin1.selection().set([bnd])
    cin1.set('c0_in', '1')
    cin1.label(f'Inlet 1 Conc - Boundary {bnd}')
    
    bc_results["inlets"].append({"boundary": bnd, "velocity": "v_in", "concentration": "1"})
    print(f"    Inlet 1: Boundary {bnd}, v=v_in, c=1")

# Inlet 2
for i, bnd in enumerate(inlet2_boundaries):
    inlet2 = spf.create(f'inl2_{i}', 'InletBoundary')
    inlet2.selection().set([bnd])
    inlet2.set('U0', 'v_in')
    inlet2.label(f'Inlet 2 - Boundary {bnd}')
    
    # Concentration = 0 at inlet 2
    cin2 = tds.create(f'cin2_{i}', 'Inflow')
    cin2.selection().set([bnd])
    cin2.set('c0_in', '0')
    cin2.label(f'Inlet 2 Conc - Boundary {bnd}')
    
    bc_results["inlets"].append({"boundary": bnd, "velocity": "v_in", "concentration": "0"})
    print(f"    Inlet 2: Boundary {bnd}, v=v_in, c=0")

# Outlet
for i, bnd in enumerate(outlet_boundaries):
    outlet = spf.create(f'out_{i}', 'OutletBoundary')
    outlet.selection().set([bnd])
    outlet.label(f'Outlet - Boundary {bnd}')
    
    bc_results["outlets"].append({"boundary": bnd, "pressure": "0"})
    print(f"    Outlet: Boundary {bnd}, p=0")

# Add study
print("\n[10] Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("\n[11] Solving...")
study.run()
print("    Solution complete!")

# Save model with version
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
version_file = MODELS_DIR / f"{MODEL_NAME}_{timestamp}.mph"
latest_file = MODELS_DIR / f"{MODEL_NAME}_latest.mph"

model.save(str(version_file))
model.save(str(latest_file))

print(f"\n[12] Model saved:")
print(f"    Version: {version_file}")
print(f"    Latest:  {latest_file}")

print("\n" + "=" * 70)
print("SIMULATION COMPLETE")
print("=" * 70)
print(f"""
Results:
  - Boundary conditions configured: {len(bc_results['inlets'])} inlets, {len(bc_results['outlets'])} outlets
  - Model saved to: {MODELS_DIR}
  
To visualize:
  1. Open {latest_file} in COMSOL GUI
  2. Add plot groups for velocity and concentration
  3. Or use the visualize script for matplotlib output
""")

client.clear()
print("Done!")
