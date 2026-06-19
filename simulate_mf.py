import mph
import numpy as np

client = mph.start(cores=6)

path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC_N300_freq.mph'
model = client.load(path)
jmodel = model.java

# Check studies
print('Studies:', list(jmodel.study().tags()))

# Solve using Java API
jmodel.study('std3').run()
print('Solved!')

# Evaluate
b = np.array(model.evaluate('mf.normB', 'dset1'))
print(f'B field: min={np.min(b):.3e} T, max={np.max(b):.3e} T, mean={np.mean(b):.3e} T')

# Save
model.save(path)
print('Saved')
