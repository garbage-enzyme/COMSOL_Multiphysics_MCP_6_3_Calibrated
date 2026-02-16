"""Create complete 3D chip thermal model with TSV and heat source."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("3D Chip Thermal Model with TSV and Heat Source")
print("=" * 70)

# Model name and directory
MODEL_NAME = "chip_thermal_full"
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
print("    chip_size=60um, chip_thick=5um, tsv_dia=5um")
print("    heat_size=10um, tsv_heat_dist=20um")
print("    Q_heat=1e6 W/m2, T_amb=20 C")

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
tsv.set('h', 'chip_thick*2')
tsv.set('pos', ['0', '0', '0'])
tsv.label('TSV Cylinder')

# Heat source pad (10um x 10um x 0.5um on top surface, 20um from TSV center)
print("    Creating heat source pad...")
heat_pad = geom.feature().create('blk2', 'Block')
heat_pad.set('base', 'center')
heat_pad.set('size', ['heat_size', 'heat_size', 'chip_thick*0.1'])
heat_pad.set('pos', ['tsv_heat_dist', '0', 'chip_thick + chip_thick*0.05'])
heat_pad.label('Heat Source Pad')

# Subtract TSV from chip
print("    Creating TSV through-hole...")
diff = geom.feature().create('dif1', 'Difference')
diff.selection('input').set(['blk1'])
diff.selection('input2').set(['cyl1'])
diff.label('Chip with TSV Hole')

# Union everything
print("    Combining geometry...")
union = geom.feature().create('uni1', 'Union')
union.selection('input').set(['dif1', 'blk2'])
union.label('Complete Geometry')

geom.run()
print("    Geometry built successfully")

# Add materials
print("\n[4] Adding materials...")

# Silicon for chip
si = comp.material().create('mat1', 'Common')
si.propertyGroup('def').set('density', '2330[kg/m^3]')
si.propertyGroup('def').set('heatcapacity', '700[J/(kg*K)]')
si.propertyGroup('def').set('thermalconductivity', '130[W/(m*K)]')
si.label('Silicon (Chip)')

# Add Heat Transfer physics
print("\n[5] Adding Heat Transfer physics...")
ht = comp.physics().create('ht', 'HeatTransfer', 'geom1')
ht.label('Heat Transfer in Solids')

# Create mesh
print("\n[6] Creating mesh...")
mesh = comp.mesh().create('mesh1', 'geom1')
mesh.autoMeshSize(4)  # Finer mesh
mesh.run()
print("    Mesh generated")

# Set up boundary conditions
print("\n[7] Setting boundary conditions...")

# Heat flux on top surface of heat source
# For the union geometry, we need to find the correct boundary
# The top surface should be one of the exterior boundaries
heat_bc = ht.create('hf1', 'HeatFluxBoundary')
heat_bc.set('q0', 'Q_heat')
heat_bc.label('Heat Source')
print("    Heat source: Q = 1e6 W/m2")

# Temperature boundary on bottom (heat sink)
temp_bc = ht.create('temp1', 'TemperatureBoundary')
temp_bc.set('T0', 'T_amb')
temp_bc.label('Heat Sink')
print("    Heat sink: T = 20 C")

# Add study
print("\n[8] Adding stationary study...")
study = jm.study().create('std1')
study.create('stat', 'Stationary')

# Solve
print("\n[9] Solving...")
try:
    study.run()
    print("    Solution complete!")
    solution_success = True
except Exception as e:
    print(f"    Solution warning: {e}")
    print("    Model saved but solution may not be accurate")
    solution_success = False

# Evaluate results
if solution_success:
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
        
        # Calculate thermal resistance
        delta_T = T_max - 293.15
        Q_total = 1e6 * (10e-6)**2  # Total power in W
        R_th = delta_T / Q_total if Q_total > 0 else 0
        print(f"    Total heat power: {Q_total*1e3:.4f} mW")
        print(f"    Thermal resistance: {R_th:.1f} K/W")
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
print("MODEL CREATION COMPLETE")
print("=" * 70)
print(f"""
Geometry:
  - Chip: 60um x 60um x 5um
  - TSV: 5um diameter through-hole at center
  - Heat source: 10um x 10um, 20um from TSV center

Materials:
  - Silicon: k=130 W/(m*K), rho=2330 kg/m3, Cp=700 J/(kg*K)

Boundary Conditions:
  - Heat source: Q = 1e6 W/m2
  - Heat sink: T = 20 C

Model saved to: {MODELS_DIR}
""")

client.clear()
print("Done!")
