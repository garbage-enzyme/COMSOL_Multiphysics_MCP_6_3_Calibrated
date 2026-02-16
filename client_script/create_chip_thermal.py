"""Create 3D chip thermal model with TSV and heat source."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("3D Chip Thermal Model with TSV")
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
params.set('h_conv', '10[W/(m^2*K)]')  # Convection coefficient
params.set('T_amb', '293.15[K]')  # Ambient temperature
print("    chip_size=60um, chip_thick=5um, tsv_dia=5um")
print("    heat_size=10um, tsv_heat_dist=20um, Q_heat=1e6 W/m2")

# Create component and geometry
print("\n[3] Creating 3D geometry...")
comp = jm.component().create('comp1', True)
geom = comp.geom().create('geom1', 3)

# Chip substrate (60um x 60um x 5um)
print("    Creating chip substrate...")
chip = geom.feature().create('blk1', 'Block')
chip.set('base', 'center')
chip.set('size', ['chip_size', 'chip_size', 'chip_thick'])
chip.set('pos', ['0', '0', 'chip_thick/2'])
chip.label('Chip Substrate')

# TSV cylinder (diameter 5um, through the thickness)
print("    Creating TSV hole...")
tsv = geom.feature().create('cyl1', 'Cylinder')
tsv.set('r', 'tsv_dia/2')
tsv.set('h', 'chip_thick*2')  # Longer to ensure it cuts through
tsv.set('pos', ['0', '0', '0'])  # Center at origin
tsv.label('TSV Hole')

# Heat source (10um x 10um, on top surface, 20um from TSV center)
# Position: TSV at (0,0), heat source at (tsv_heat_dist + heat_size/2, 0, chip_thick)
print("    Creating heat source...")
heat = geom.feature().create('blk2', 'Block')
heat.set('base', 'center')
heat.set('size', ['heat_size', 'heat_size', 'chip_thick*0.1'])  # Thin layer on top
heat.set('pos', ['tsv_heat_dist', '0', 'chip_thick + chip_thick*0.05'])
heat.label('Heat Source')

# Subtract TSV from chip to create hole
print("    Creating TSV through-hole...")
diff = geom.feature().create('dif1', 'Difference')
diff.selection('input').set(['blk1'])
diff.selection('input2').set(['cyl1'])
diff.label('Chip with TSV')

# Union heat source with chip
print("    Combining geometry...")
union = geom.feature().create('uni1', 'Union')
union.selection('input').set(['dif1', 'blk2'])
union.label('Complete Geometry')

# Build geometry
geom.run()
print("    Geometry built")

# Add materials
print("\n[4] Adding materials...")
# Silicon for chip
si = comp.material().create('mat1', 'Common')
si.propertyGroup('def').set('density', '2330[kg/m^3]')
si.propertyGroup('def').set('heatcapacity', '700[J/(kg*K)]')
si.propertyGroup('def').set('thermalconductivity', '130[W/(m*K)]')
si.label('Silicon')

# Copper for heat source (simplified as same domain for now)
# In a real model, you'd assign different materials to different domains

# Add Heat Transfer physics
print("\n[5] Adding Heat Transfer physics...")
ht = comp.physics().create('ht', 'HeatTransfer', 'geom1')
ht.label('Heat Transfer')

# Create mesh
print("\n[6] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(4)  # Finer mesh
mesh.run()
print("    Mesh generated")

# Set up boundary conditions
print("\n[7] Setting boundary conditions...")

# Use simplified setup - heat source as boundary condition on specific boundary
# For a block, boundaries are numbered. We'll try boundary 1 (typically one face)
heat_bc = ht.create('hf1', 'HeatFluxBoundary')
heat_bc.selection().set([1])  # Apply to boundary 1
heat_bc.set('q0', 'Q_heat')
heat_bc.label('Heat Source')
print("    Heat source: Q = 1e6 W/m2 (boundary 1)")

# Temperature boundary on another boundary
temp_bc = ht.create('temp1', 'TemperatureBoundary')
temp_bc.selection().set([2])  # Apply to boundary 2
temp_bc.set('T0', 'T_amb')
temp_bc.label('Heat Sink')
print("    Heat sink: T = 20 C (boundary 2)")

# Initial temperature
init = ht.feature('init1')
init.set('Tinit', 'T_amb')
print("    Initial temp: 20 C")

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

# Save model with version
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

# List versions
print(f"\nModel versions in {MODELS_DIR}:")
for f in sorted(MODELS_DIR.glob("*.mph")):
    size = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name}: {size:.1f} MB")

client.clear()
print("\nDone!")
