"""Add visualization plot groups to chip thermal model."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("Adding Visualization to Chip Thermal Model")
print("=" * 70)

# Load existing model
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_PATH = PROJECT_ROOT / "comsol_models" / "chip_tsv_thermal" / "chip_tsv_thermal_latest.mph"

print(f"\nLoading model: {MODEL_PATH}")
client = mph.start(cores=4)
model = client.load(str(MODEL_PATH))
jm = model.java
print(f"Model: {model.name()}")

# Get results node
results = jm.result()

print("\n[1] Creating Temperature Surface Plot...")
# Create 3D Plot Group for temperature distribution
pg1 = results.create('pg1', 'PlotGroup3D')
pg1.label('Temperature Distribution')

# Add surface plot
surf1 = pg1.create('surf1', 'Surface')
surf1.set('expr', 'T')
surf1.set('unit', 'degC')
surf1.set('descr', 'Temperature')
surf1.set('colortable', 'Thermal')
surf1.set('colorlegend', True)
print("    Surface plot created")

print("\n[2] Creating Temperature Slice Plot...")
# Create slice plot
pg2 = results.create('pg2', 'PlotGroup3D')
pg2.label('Temperature Slices')

slice1 = pg2.create('slc1', 'Slice')
slice1.set('expr', 'T')
slice1.set('unit', 'degC')
slice1.set('descr', 'Temperature')
slice1.set('colortable', 'Thermal')
print("    Slice plot created")

print("\n[3] Creating Temperature Isosurface Plot...")
# Create isosurface plot
pg3 = results.create('pg3', 'PlotGroup3D')
pg3.label('Temperature Isosurfaces')

iso1 = pg3.create('iso1', 'Isosurface')
iso1.set('expr', 'T')
iso1.set('unit', 'degC')
iso1.set('descr', 'Temperature')
iso1.set('colortable', 'Thermal')
print("    Isosurface plot created")

print("\n[4] Creating Heat Flux Arrow Plot...")
# Create arrow plot for heat flux
pg4 = results.create('pg4', 'PlotGroup3D')
pg4.label('Heat Flux Vectors')

# First add temperature surface
surf2 = pg4.create('surf2', 'Surface')
surf2.set('expr', 'T')
surf2.set('unit', 'degC')
surf2.set('colortable', 'Thermal')

# Add arrow volume for heat flux
arrow1 = pg4.create('arwv1', 'ArrowVolume')
arrow1.set('expr', ['ht.qx', 'ht.qy', 'ht.qz'])
arrow1.set('descr', 'Heat flux')
print("    Heat flux arrow plot created")

print("\n[5] Creating 2D Line Plot (Temperature along centerline)...")
# Create 1D plot group for line graph
pg5 = results.create('pg5', 'PlotGroup1D')
pg5.label('Temperature Profile')

# Create line graph along x-axis through center
line1 = pg5.create('lg1', 'LineGraph')
line1.set('expr', 'T')
line1.set('unit', 'degC')
line1.set('descr', 'Temperature')
line1.set('xdata', 'expr')
line1.set('xdataexpr', 'x')
print("    Line plot created")

print("\n[6] Running plot generation...")
# Run all plots
for pg in [pg1, pg2, pg3, pg4, pg5]:
    try:
        pg.run()
        print(f"    {pg.label()} - OK")
    except Exception as e:
        print(f"    {pg.label()} - Warning: {e}")

# Save model with plots
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
version_file = Path(__file__).parent / "comsol_models" / "chip_tsv_thermal" / f"chip_tsv_thermal_{timestamp}.mph"

model.save(str(version_file))

print(f"\n[7] Model saved:")
print(f"    {version_file}")

print("\n" + "=" * 70)
print("VISUALIZATION COMPLETE")
print("=" * 70)
print("""
Created Plot Groups:
1. Temperature Distribution - 3D surface plot
2. Temperature Slices - Cross-section slices
3. Temperature Isosurfaces - Isothermal surfaces
4. Heat Flux Vectors - Arrows showing heat flow direction
5. Temperature Profile - 1D line graph

To view in COMSOL GUI:
1. Open the model file
2. Go to Results > Plot Groups
3. Double-click any plot group to visualize
""")

client.clear()
print("Done!")
