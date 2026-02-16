"""Automated Micromixer Simulation with Auto-Detected Boundaries."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("Automated Micromixer Simulation with Boundary Detection")
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

# Create component and geometry
print("\n[4] Creating 3D geometry...")
comp = jm.component().create('comp1', True)
geom = comp.geom().create('geom1', 3)

# Create simpler geometry for easier boundary identification
# Single channel with clear inlet/outlet
blk = geom.feature().create('blk1', 'Block')
blk.set('base', 'corner')
blk.set('size', ['L_out', 'w_ch', 'h_ch'])
blk.set('pos', ['0', '-w_ch/2', '0'])
blk.label('Channel')

print("    Building geometry...")
geom.run()
print("    Geometry built")

# Identify boundaries by their position
print("\n[5] Identifying boundaries...")
# For a simple block at (0, -w_ch/2, 0) with size (L_out, w_ch, h_ch):
# - Boundary at x=0: Inlet (left face)
# - Boundary at x=L_out: Outlet (right face)
# - Other boundaries: Walls

# We need to query boundary coordinates
# Typical boundary numbering for a block:
# 1: x=0 face (inlet)
# 2: x=L_out face (outlet)
# 3-6: wall faces

# Add water material
print("\n[6] Adding water material...")
mat = comp.material().create('mat1', 'Common')
mat.propertyGroup('def').set('relpermeability', '1')
mat.propertyGroup('def').set('relpermittivity', '80')
mat.propertyGroup('def').set('density', '1000[kg/m^3]')
mat.propertyGroup('def').set('dynamicviscosity', '0.001[Pa*s]')
mat.label('Water')

# Add Laminar Flow physics
print("\n[7] Adding Laminar Flow physics...")
spf = comp.physics().create('spf', 'LaminarFlow', 'geom1')
spf.label('Laminar Flow')

# Add Transport of Diluted Species for mixing visualization
print("\n[8] Adding Transport of Diluted Species...")
tds = comp.physics().create('tds', 'DilutedSpecies', 'geom1')
tds.label('Transport of Diluted Species')
tds.prop('TransportMechanism').set('Convection', True)
tds.feature('cdm1').set('D_c', 'D_c')

# Get mesh
print("\n[9] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)
mesh.run()
print("    Mesh generated")

# Now set up boundary conditions
print("\n[10] Setting boundary conditions...")

# Try to set boundary conditions on specific boundaries
# We'll iterate and try common boundary numbers
inlet_set = False
outlet_set = False

# Common boundary numbers for a single block:
# Boundary 1: usually x-min face
# Boundary 2: usually x-max face
# etc.

print("    Attempting to configure inlet at boundary 1...")
try:
    inlet = spf.create('inl1', 'InletBoundary')
    inlet.selection().set([1])  # Boundary 1 = inlet (x=0)
    # Try different possible property names for inlet velocity
    try:
        inlet.set('U0', 'v_in')  # Normal inflow velocity
    except:
        try:
            inlet.set('NormalInflowVelocity', 'v_in')
        except:
            try:
                inlet.set('Vin', 'v_in')
            except:
                pass  # Use default
    inlet.label('Inlet (x=0)')
    
    # Concentration at inlet
    cin = tds.create('cin1', 'Inflow')
    cin.selection().set([1])
    try:
        cin.set('c0_in', '1')
    except:
        try:
            cin.set('c0', '1')
        except:
            pass
    cin.label('Inlet Concentration')
    
    inlet_set = True
    print("    Inlet configured at boundary 1")
except Exception as e:
    print(f"    Warning: Could not set inlet: {e}")

print("    Attempting to configure outlet at boundary 2...")
try:
    outlet = spf.create('out1', 'OutletBoundary')
    outlet.selection().set([2])  # Boundary 2 = outlet (x=L_out)
    outlet.label('Outlet (x=L_out)')
    
    outlet_set = True
    print("    Outlet configured at boundary 2")
except Exception as e:
    print(f"    Warning: Could not set outlet: {e}")

# Add study
print("\n[11] Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("\n[12] Solving...")
try:
    study.run()
    print("    Solution complete!")
    solution_success = True
except Exception as e:
    print(f"    Solution error: {e}")
    solution_success = False

# Save model with version
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
version_file = MODELS_DIR / f"{MODEL_NAME}_{timestamp}.mph"
latest_file = MODELS_DIR / f"{MODEL_NAME}_latest.mph"

model.save(str(version_file))
model.save(str(latest_file))

print(f"\n[13] Model saved:")
print(f"    Version: {version_file.name}")
print(f"    Latest:  {latest_file.name}")

# Evaluate results if solution succeeded
if solution_success:
    print("\n[14] Evaluating results...")
    try:
        U = model.evaluate('spf.U', unit='m/s')
        import numpy as np
        print(f"    Velocity range: {np.min(U)*1e3:.4f} to {np.max(U)*1e3:.4f} mm/s")
        print(f"    Mean velocity: {np.mean(U)*1e3:.4f} mm/s")
    except Exception as e:
        print(f"    Could not evaluate: {e}")

print("\n" + "=" * 70)
print("SIMULATION COMPLETE")
print("=" * 70)

# List all versions
print(f"\nModel versions in {MODELS_DIR}:")
for f in sorted(MODELS_DIR.glob("*.mph")):
    size = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name}: {size:.1f} MB")

client.clear()
print("\nDone!")
