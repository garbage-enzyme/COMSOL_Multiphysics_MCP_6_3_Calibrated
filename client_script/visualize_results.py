"""Visualize micromixer simulation results - simplified version."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph

print("Loading micromixer model...")
client = mph.start(cores=4)
model = client.load('micromixer_simple.mph')
print(f"Model loaded: {model.name()}")

# Get Java model
jm = model.java

# Create plot group for velocity
print("\nCreating velocity magnitude plot...")
results = jm.result()

# Create 3D Plot Group with Surface plot
plot1 = results.create('pg1', 'PlotGroup3D')
plot1.label('Velocity Magnitude')

# Add surface plot - shows velocity on all surfaces
surf1 = plot1.create('surf1', 'Surface')
surf1.set('expr', 'spf.U')
surf1.set('unit', 'm/s')
surf1.label('Velocity')
print("  Surface plot created")

# Create a second plot group with volume rendering
print("\nCreating volume plot...")
plot2 = results.create('pg2', 'PlotGroup3D')
plot2.label('Velocity Volume')

vol1 = plot2.create('vol1', 'Volume')
vol1.set('expr', 'spf.U')
vol1.set('unit', 'm/s')
vol1.label('Velocity Field')
print("  Volume plot created")

# Create arrow plot for velocity vectors
print("\nCreating velocity arrow plot...")
plot3 = results.create('pg3', 'PlotGroup3D')
plot3.label('Velocity Vectors')

arrow1 = plot3.create('arwv1', 'ArrowVolume')
arrow1.set('expr', ['u', 'v', 'w'])
arrow1.label('Velocity Arrows')
print("  Arrow plot created")

# Run the plots to generate data
print("\nRunning plot rendering...")
try:
    plot1.run()
    plot2.run()
    plot3.run()
    print("  All plots rendered")
except Exception as e:
    print(f"  Warning: {e}")

# Export images
print("\nExporting visualization images...")

# Export surface plot
try:
    export1 = results.create('img1', 'Image')
    export1.set('plot', 'pg1')
    export1.set('filename', 'velocity_surface.png')
    export1.set('pngwidth', 1200)
    export1.set('pngheight', 900)
    export1.run()
    print("  Saved: velocity_surface.png")
except Exception as e:
    print(f"  Surface export error: {e}")

# Export volume plot
try:
    export2 = results.create('img2', 'Image')
    export2.set('plot', 'pg2')
    export2.set('filename', 'velocity_volume.png')
    export2.set('pngwidth', 1200)
    export2.set('pngheight', 900)
    export2.run()
    print("  Saved: velocity_volume.png")
except Exception as e:
    print(f"  Volume export error: {e}")

# Export arrow plot
try:
    export3 = results.create('img3', 'Image')
    export3.set('plot', 'pg3')
    export3.set('filename', 'velocity_arrows.png')
    export3.set('pngwidth', 1200)
    export3.set('pngheight', 900)
    export3.run()
    print("  Saved: velocity_arrows.png")
except Exception as e:
    print(f"  Arrow export error: {e}")

# Save model with plots
model.save('micromixer_visualized.mph')
print("\nModel saved with plots: micromixer_visualized.mph")

# List generated files
import os
print("\nGenerated files:")
for f in ['velocity_surface.png', 'velocity_volume.png', 'velocity_arrows.png']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: {size/1024:.1f} KB")

client.clear()
print("\nDone!")
