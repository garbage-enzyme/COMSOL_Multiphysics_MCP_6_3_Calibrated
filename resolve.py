import mph
import numpy as np
import os

client = mph.start(cores=6)

path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC_N300_freq.mph'
model = client.load(path)
jmodel = model.java
comp1 = jmodel.component('comp1')
mf = comp1.physics('mf')

# Solve
print('Solving...')
jmodel.study('std3').run()
print('Solved!')

# Evaluate
b = model.evaluate('mf.normB', 'dset1')
print(f'B: min={np.min(b):.3e}, max={np.max(b):.3e} T')

# Save
model.save(path)
print(f'Saved: {path}')
print(f'File size: {os.path.getsize(path)} bytes')
