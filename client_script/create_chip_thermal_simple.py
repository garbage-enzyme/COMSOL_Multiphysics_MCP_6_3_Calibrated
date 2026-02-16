"""Create simplified 3D chip thermal model."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("3D Chip Thermal Model (Simplified)")
print("=" * 70)

# Model name and directory
MODEL_NAME = "chip_thermal"
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "comsol_models" / MODEL_NAME
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print(f"\nModel directory: {MODELS_DIR}")

# Start COMSOL
print("\n[1] Starting COMSOL...")
client = mph.start(cores=4)
model = client.create(MODEL_NAME)
jm = model.java
print(f"    Model: {model.name()}")

# Parameters
print("\n[2] Setting parameters...")
params = jm.param()
params.set('chip_size', '60[um]')
params.set('chip_thick', '5[um]')
params.set('tsv_dia', '5[um]')
params.set('heat_size', '10[um]')
params.set('tsv_heat_dist', '20[um]')
params.set('Q_heat', '1e6[W/m^2]')
params.set('T_amb', '293.15[K]')
print("    Parameters set")

# Create component and geometry
print("\n[3] Creating 3D geometry...")
comp = jm.component().create('comp1', True)
geom = comp.geom().create('geom1', 3)

# Simple chip substrate without TSV hole first
print("    Creating chip substrate...")
chip = geom.feature().create('blk1', 'Block')
chip.set('base', 'center')
chip.set('size', ['chip_size', 'chip_size', 'chip_thick'])
chip.set('pos', ['0', '0', 'chip_thick/2'])
chip.label('Chip Substrate')

geom.run()
print("    Geometry built")

# Add material
print("\n[4] Adding Silicon material...")
si = comp.material().create('mat1', 'Common')
si.propertyGroup('def').set('density', '2330[kg/m^3]')
si.propertyGroup('def').set('heatcapacity', '700[J/(kg*K)]')
si.propertyGroup('def').set('thermalconductivity', '130[W/(m*K)]')
si.label('Silicon')

# Add Heat Transfer physics
print("\n[5] Adding Heat Transfer physics...")
ht = comp.physics().create('ht', 'HeatTransfer', 'geom1')
ht.label('Heat Transfer')

# Create mesh
print("\n[6] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)
mesh.run()
print("    Mesh generated")

# Set up boundary conditions
print("\n[7] Setting boundary conditions...")
# For a block, boundaries are numbered 1-6:
# 1: x=0 face, 2: x=L face
# 3: y=0 face, 4: y=L face
# 5: z=0 face (bottom), 6: z=H face (top)

# Heat flux on top surface (boundary 6 - z = chip_thick)
heat_bc = ht.create('hf1', 'HeatFluxBoundary')
heat_bc.selection().set([6])  # Top surface
heat_bc.set('q0', 'Q_heat')
heat_bc.label('Heat Source (Top)')
print("    Heat source: Q = 1e6 W/m2 (top surface)")

# Temperature boundary on bottom (boundary 5 - z = 0)
temp_bc = ht.create('temp1', 'TemperatureBoundary')
temp_bc.selection().set([5])  # Bottom surface
temp_bc.set('T0', 'T_amb')
temp_bc.label('Heat Sink (Bottom)')
print("    Heat sink: T = 20 C (bottom surface)")

# Add study
print("\n[8] Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("\n[9] Solving...")
study.run()
print("    Solution complete!")

# Evaluate results
print("\n[10] Evaluating results...")
try:
    T = model.evaluate('T', unit='K')
    import numpy as np
    T_min = np.min(T)
    T_max = np.max(T)
    T_avg = np.mean(T)
    print(f"    Temperature range: {T_min-273.15:.2f} C to {T_max-273.15:.2f} C")
    print(f"    Average temperature: {T_avg-273.15:.2f} C")
    print(f"    Temperature rise: {T_max-T_min:.2f} K")
except Exception as e:
    print(f"    Could not evaluate: {e}")

# Save model
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
version_file = MODELS_DIR / f"{MODEL_NAME}_{timestamp}.mph"
latest_file = MODELS_DIR / f"{MODEL_NAME}_latest.mph"

model.save(str(version_file))
model.save(str(latest_file))

print(f"\n[11] Model saved:")
print(f"    Version: {version_file.name}")
print(f"    Latest:  {latest_file.name}")

print("\n" + "=" * 70)
print("SIMULATION COMPLETE")
print("=" * 70)

client.clear()
print("\nDone!")
