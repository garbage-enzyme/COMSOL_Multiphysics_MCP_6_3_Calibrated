"""Visualize micromixer results using matplotlib."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

print("Loading micromixer model...")
client = mph.start(cores=4)
model = client.load('micromixer_simple.mph')
print(f"Model loaded: {model.name()}")

# Get evaluation points on a grid
print("\nEvaluating velocity field on grid...")

# Create evaluation dataset
jm = model.java
results = jm.result()

# Create a cut plane dataset for xy-plane at z = h_ch/2
print("Creating cut plane dataset...")
cut_plane = results.dataset().create('cpl1', 'CutPlane')
cut_plane.set('plane', 'xy')
cut_plane.set('z', 'h_ch/2')

# Create evaluation
try:
    # Evaluate velocity magnitude on the cut plane
    print("Evaluating velocity magnitude...")
    eval_node = results.create('eval1', 'Evaluation')
    eval_node.set('expr', 'spf.U')
    eval_node.set('unit', 'm/s')
    eval_node.set('dataset', 'cpl1')
    
    # Get data
    data = eval_node.getData()
    print(f"Data shape: {data.shape if hasattr(data, 'shape') else 'N/A'}")
except Exception as e:
    print(f"Evaluation error: {e}")
    print("Using alternative method...")

# Alternative: use mph's evaluate function
try:
    print("\nTrying mph evaluate method...")
    # Get velocity at specific points
    u = model.evaluate('spf.U', unit='m/s')
    print(f"Velocity magnitude range: {np.min(u):.6f} to {np.max(u):.6f} m/s")
except Exception as e:
    print(f"mph evaluate error: {e}")

# Create 2D grid evaluation
print("\nCreating 2D grid for visualization...")

# Get geometry bounds
geom = jm.component('comp1').geom('geom1')
geom.run()

# Create cut point dataset for line evaluation
print("Creating line evaluation...")
try:
    # Create parametric curve for line data
    param = results.dataset().create('pc1', 'ParametricCurve')
    param.set('parname', 's')
    param.set('parmin', '0')
    param.set('parmax', '1')
    param.set('xexpr', 's*L_out')
    param.set('yexpr', '0')
    param.set('zexpr', 'h_ch/2')
    
    # Evaluate along the line
    eval_line = results.numerical().create('gev1', 'EvalGlobal')
    eval_line.set('expr', ['x', 'spf.U', 'u', 'v', 'w'])
    eval_line.set('unit', ['m', 'm/s', 'm/s', 'm/s', 'm/s'])
    eval_line.set('dataset', 'pc1')
    eval_line.setResult()
    
    # Get results
    line_data = eval_line.getResult()
    print(f"Line data obtained: {type(line_data)}")
    
    # Convert to numpy
    x_vals = []
    u_vals = []
    for i in range(line_data.length()):
        row = line_data.get(i)
        x_vals.append([row.get(j) for j in range(row.length())])
    
    x_arr = np.array(x_vals)
    print(f"Data shape: {x_arr.shape}")
    
    # Plot velocity along centerline
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x_arr[:, 0]*1e6, x_arr[:, 1]*1e3, 'b-', linewidth=2)
    ax.set_xlabel('x Position (μm)', fontsize=12)
    ax.set_ylabel('Velocity Magnitude (mm/s)', fontsize=12)
    ax.set_title('Velocity Along Channel Centerline', fontsize=14)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('velocity_centerline.png', dpi=150, bbox_inches='tight')
    print("Saved: velocity_centerline.png")
    
except Exception as e:
    print(f"Line evaluation error: {e}")
    import traceback
    traceback.print_exc()

# Create summary statistics plot
print("\nCreating summary visualization...")
try:
    # Get some global statistics
    stats = results.numerical().create('gev2', 'EvalGlobal')
    stats.set('expr', [
        'sqrt(spf.U_max^2)',  # Max velocity
        'sqrt(spf.U_min^2)',  # Min velocity  
        'spf.U_avg',          # Average velocity
    ])
    stats.set('descr', ['Max velocity', 'Min velocity', 'Avg velocity'])
    stats.set('unit', ['m/s', 'm/s', 'm/s'])
    stats.setResult()
    
    result = stats.getResult()
    max_u = result.get(0).get(0)
    min_u = result.get(1).get(0)
    avg_u = result.get(2).get(0)
    
    print(f"\nVelocity Statistics:")
    print(f"  Max: {max_u*1e3:.4f} mm/s")
    print(f"  Min: {min_u*1e3:.4f} mm/s")
    print(f"  Avg: {avg_u*1e3:.4f} mm/s")
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(8, 6))
    labels = ['Max', 'Avg', 'Min']
    values = [max_u*1e3, avg_u*1e3, min_u*1e3]
    colors = ['#ff6b6b', '#4ecdc4', '#95afc0']
    bars = ax.bar(labels, values, color=colors, edgecolor='black', linewidth=1.2)
    
    ax.set_ylabel('Velocity (mm/s)', fontsize=12)
    ax.set_title('Velocity Statistics Summary', fontsize=14)
    ax.set_ylim(0, max(values)*1.2)
    
    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.4f}', ha='center', va='bottom', fontsize=11)
    
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig('velocity_statistics.png', dpi=150, bbox_inches='tight')
    print("Saved: velocity_statistics.png")
    
except Exception as e:
    print(f"Statistics error: {e}")
    import traceback
    traceback.print_exc()

# Save model
model.save('micromixer_analyzed.mph')
print("\nModel saved: micromixer_analyzed.mph")

client.clear()
print("\nDone!")
