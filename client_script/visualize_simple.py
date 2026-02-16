"""Simple visualization using mph and matplotlib."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import mph
import numpy as np
import matplotlib.pyplot as plt

print("=" * 60)
print("Micromixer Results Visualization")
print("=" * 60)

print("\nLoading model...")
client = mph.start(cores=4)
model = client.load('micromixer_simple.mph')
print(f"Model: {model.name()}")

# Get model parameters
jm = model.java
# Use hardcoded values (from model parameters)
w_ch = 100e-6  # 100 um
h_ch = 50e-6   # 50 um
L_out = 600e-6 # 600 um
v_in = 1e-3    # 1 mm/s

print(f"\nChannel geometry:")
print(f"  Width: {w_ch*1e6:.1f} um")
print(f"  Height: {h_ch*1e6:.1f} um")
print(f"  Length: {L_out*1e6:.1f} um")
print(f"  Inlet velocity: {v_in*1e3:.2f} mm/s")

# Evaluate velocity field
print("\nEvaluating velocity field...")
try:
    # Get all velocity data points
    u_data = model.evaluate('u', unit='m/s')  # x-velocity
    v_data = model.evaluate('v', unit='m/s')  # y-velocity
    w_data = model.evaluate('w', unit='m/s')  # z-velocity
    U_mag = model.evaluate('spf.U', unit='m/s')  # magnitude
    
    print(f"  Data points: {len(U_mag)}")
    print(f"  Max velocity: {np.max(np.abs(U_mag))*1e3:.4f} mm/s")
    print(f"  Min velocity: {np.min(np.abs(U_mag))*1e3:.4f} mm/s")
    print(f"  Mean velocity: {np.mean(np.abs(U_mag))*1e3:.4f} mm/s")
    
    # Create histogram of velocity distribution
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Velocity magnitude histogram
    ax1 = axes[0]
    ax1.hist(U_mag.flatten()*1e3, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Velocity Magnitude (mm/s)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Velocity Distribution', fontsize=14)
    ax1.axvline(np.mean(U_mag)*1e3, color='red', linestyle='--', label=f'Mean: {np.mean(U_mag)*1e3:.4f} mm/s')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Right: Velocity components comparison
    ax2 = axes[1]
    components = ['u (x)', 'v (y)', 'w (z)']
    means = [np.mean(np.abs(u_data))*1e3, np.mean(np.abs(v_data))*1e3, np.mean(np.abs(w_data))*1e3]
    stds = [np.std(u_data)*1e3, np.std(v_data)*1e3, np.std(w_data)*1e3]
    
    x_pos = np.arange(len(components))
    bars = ax2.bar(x_pos, means, yerr=stds, capsize=5, color=['#3498db', '#2ecc71', '#e74c3c'], 
                   edgecolor='black', linewidth=1)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(components)
    ax2.set_ylabel('Mean Absolute Velocity (mm/s)', fontsize=12)
    ax2.set_title('Velocity Components', fontsize=14)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('velocity_analysis.png', dpi=150, bbox_inches='tight')
    print("\nSaved: velocity_analysis.png")
    
    # Create Reynolds number plot
    print("\nCalculating Reynolds number...")
    rho = 1000  # kg/m^3 (water)
    mu = 0.001  # Pa*s (water)
    D_h = 2 * w_ch * h_ch / (w_ch + h_ch)  # Hydraulic diameter
    Re = rho * v_in * D_h / mu
    
    print(f"  Hydraulic diameter: {D_h*1e6:.1f} um")
    print(f"  Reynolds number: {Re:.2f}")
    print(f"  Flow regime: {'Laminar' if Re < 2300 else 'Transitional' if Re < 4000 else 'Turbulent'}")
    
    # Summary figure
    fig, ax = plt.subplots(figsize=(10, 6))
    summary_text = f"""Micromixer Simulation Results
    
Channel Geometry:
  Width: {w_ch*1e6:.1f} μm
  Height: {h_ch*1e6:.1f} μm
  Length: {L_out*1e6:.1f} μm

Flow Conditions:
  Inlet velocity: {v_in*1e3:.2f} mm/s
  Hydraulic diameter: {D_h*1e6:.1f} μm
  Reynolds number: {Re:.2f}

Velocity Results:
  Maximum: {np.max(np.abs(U_mag))*1e3:.4f} mm/s
  Mean: {np.mean(np.abs(U_mag))*1e3:.4f} mm/s
  Minimum: {np.min(np.abs(U_mag))*1e3:.4f} mm/s

Flow Regime: {'Laminar' if Re < 2300 else 'Transitional' if Re < 4000 else 'Turbulent'}
"""
    
    ax.text(0.1, 0.5, summary_text, transform=ax.transAxes, fontsize=12,
            verticalalignment='center', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax.axis('off')
    ax.set_title('Simulation Summary', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('simulation_summary.png', dpi=150, bbox_inches='tight')
    print("Saved: simulation_summary.png")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Save analyzed model
model.save('micromixer_analyzed.mph')
print("\nModel saved: micromixer_analyzed.mph")

client.clear()
print("\nDone!")

# Show file sizes
import os
print("\nGenerated files:")
for f in ['velocity_analysis.png', 'simulation_summary.png']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: {size/1024:.1f} KB")
