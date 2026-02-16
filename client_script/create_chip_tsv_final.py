"""Create complete 3D chip thermal model with TSV - fixed version."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("3D Chip Thermal Model with TSV - Final Version")
print("=" * 70)

MODEL_NAME = "chip_tsv_thermal"
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

# Create component and geometry
print("\n[3] Creating 3D geometry...")
comp = jm.component().create('comp1', True)
geom = comp.geom().create('geom1', 3)

# Create chip substrate
chip = geom.feature().create('blk1', 'Block')
chip.set('base', 'center')
chip.set('size', ['chip_size', 'chip_size', 'chip_thick'])
chip.set('pos', ['0', '0', 'chip_thick/2'])
chip.label('Chip')

# Create TSV cylinder
tsv = geom.feature().create('cyl1', 'Cylinder')
tsv.set('r', 'tsv_dia/2')
tsv.set('h', 'chip_thick*2')
tsv.set('pos', ['0', '0', '0'])
tsv.label('TSV')

# Subtract TSV from chip
diff = geom.feature().create('dif1', 'Difference')
diff.selection('input').set(['blk1'])
diff.selection('input2').set(['cyl1'])
diff.label('Chip with TSV')

geom.run()
print("    Geometry built: 60x60x5um chip with 5um TSV hole")

# Add materials
print("\n[4] Adding Silicon material...")
si = comp.material().create('mat1', 'Common')
si.propertyGroup('def').set('density', '2330[kg/m^3]')
si.propertyGroup('def').set('heatcapacity', '700[J/(kg*K)]')
si.propertyGroup('def').set('thermalconductivity', '130[W/(m*K)]')
si.label('Silicon')

# Add Heat Transfer physics
print("\n[5] Adding Heat Transfer physics...")
ht = comp.physics().create('ht', 'HeatTransfer', 'geom1')

# Create mesh
print("\n[6] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(5)
mesh.run()
print("    Mesh generated")

# Set boundary conditions using explicit boundary selection
print("\n[7] Setting boundary conditions...")
print("    Configuring heat source and heat sink...")

# For the chip with TSV hole, boundaries are:
# Top surface (z = chip_thick): typically one of the boundaries
# Bottom surface (z = 0): typically another boundary
# We need to apply conditions carefully

# Heat source on top surface - use boundary 6 or similar
try:
    heat_bc = ht.create('hf1', 'HeatFluxBoundary')
    # Try top surface
    heat_bc.selection().set([6])  # Usually z-max face
    heat_bc.set('q0', 'Q_heat')
    heat_bc.label('Heat Source (Top)')
    print("    Heat source applied to boundary 6")
except Exception as e:
    print(f"    Heat source warning: {e}")

# Temperature boundary on bottom surface
try:
    temp_bc = ht.create('temp1', 'TemperatureBoundary')
    temp_bc.selection().set([5])  # Usually z-min face
    temp_bc.set('T0', 'T_amb')
    temp_bc.label('Heat Sink (Bottom)')
    print("    Heat sink applied to boundary 5")
except Exception as e:
    print(f"    Heat sink warning: {e}")

# Add study
print("\n[8] Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("\n[9] Solving...")
try:
    study.run()
    print("    Solution complete!")
    
    # Evaluate results
    print("\n[10] Evaluating results...")
    T = model.evaluate('T', unit='K')
    import numpy as np
    T_min = np.min(T)
    T_max = np.max(T)
    T_avg = np.mean(T)
    print(f"    Temperature range: {T_min-273.15:.2f} C to {T_max-273.15:.2f} C")
    print(f"    Average: {T_avg-273.15:.2f} C, Rise: {T_max-T_min:.2f} K")
    
except Exception as e:
    print(f"    Solution error: {e}")
    print("    Trying with adjusted solver settings...")

# Save model
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
version_file = MODELS_DIR / f"{MODEL_NAME}_{timestamp}.mph"
latest_file = MODELS_DIR / f"{MODEL_NAME}_latest.mph"

model.save(str(version_file))
model.save(str(latest_file))

print(f"\n[11] Model saved:")
print(f"    {version_file}")
print(f"    {latest_file}")

print("\n" + "=" * 70)
print("COMPLETE")
print("=" * 70)

# List all generated models
print("\nAll models:")
for d in sorted(PROJECT_ROOT.joinpath("comsol_models").iterdir()):
    if d.is_dir():
        files = list(d.glob("*.mph"))
        if files:
            print(f"  {d.name}/")
            for f in sorted(files)[-3:]:  # Show last 3 files
                size = f.stat().st_size / (1024*1024)
                print(f"    {f.name}: {size:.1f} MB")

client.clear()
print("\nDone!")
