import mph
import numpy as np

client = mph.start(cores=6)

path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC_N300_freq.mph'
model = client.load(path)
jmodel = model.java
comp1 = jmodel.component('comp1')
mf = comp1.physics('mf')
geom = comp1.geom('geom1')

# Boundaries: for 3 rectangles in 2D, each has 4 edges counterclockwise from bottom
# Air rect (r=[0,30], z=[-15,35]): boundaries 1=bottom, 2=right, 3=top, 4=left(axis)
# Coil1 rect (r=[8,10], z=[5,15]): boundaries 5-8
# Coil2 rect (r=[18,20], z=[5,15]): boundaries 9-12
# 
# So: axis=bnd4, exterior=bnd1,2,3, interior=bnd5-12
print('  Axis: boundary 4')
print('  Exterior: boundaries 1,2,3')
print('  Interior: boundaries 5-12')

# Now fix selections
print('\n=== Fixing Selections ===')
# axi1 is auto (identifies axis at r=0), selection not editable - skip

# fsp1 should be on exterior boundaries
fsp1 = mf.feature('fsp1')
fsp1.selection().set([1, 2, 3])
print(f'fsp1 -> boundaries [1,2,3] (exterior)')

# fsp1 on exterior boundaries (1-bottom, 2-right, 3-top)
# Not on axis (4) since axi handles it
fsp1 = mf.feature('fsp1')
fsp1.selection().set([1, 2, 3])
print(f'fsp1 -> boundaries [1,2,3] (exterior)')

# mi1 should be removed or set to empty (fsp1 handles open boundaries)
try:
    mf.feature().remove('mi1')
    print('mi1 removed (FreeSpace handles exterior)')
except:
    pass

# init1 should cover all domains
init1 = mf.feature('init1')
init1.selection().set([1, 2, 3])
print(f'init1 -> domains [1,2,3]')

print('\n=== Solve ===')
try:
    jmodel.study('std3').run()
    print('Solved!')
    b = model.evaluate('mf.normB', 'dset1')
    print(f'B: min={np.min(b):.3e}, max={np.max(b):.3e} T')
    
    # Also check phase angle
    try:
        b_phase = model.evaluate('mf.normBphase', 'dset1')
        print(f'B phase: min={np.min(b_phase):.1f}, max={np.max(b_phase):.1f} deg')
    except:
        pass
except Exception as e:
    print(f'Solve failed: {str(e)[:500]}')

path_out = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC_N300_freq.mph'
model.save(path_out)
print(f'Saved: {path_out}')
