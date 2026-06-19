import mph

client = mph.start(cores=6)

model_path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_Complete.mph'
model = client.load(model_path)

jmodel = model.java

# Use InductionCurrents instead of MagneticFields
print('Creating MagneticFields (InductionCurrents) physics...')
jmodel.component('comp1').physics().create('mf', 'InductionCurrents')
print('Success! Physics created.')

mf = jmodel.component('comp1').physics('mf')
print('Features:', mf.feature().tags())

mfi1 = mf.create('mfi1', 'MultiTurnCoil', 1)
mfi1.set('Icoil', '1[A]')
mfi1.selection().set([1])
print('Coil 1: domain 1, Icoil=1A')

mfi2 = mf.create('mfi2', 'MultiTurnCoil', 2)
mfi2.set('Icoil', '-1[A]')
mfi2.selection().set([2])
print('Coil 2: domain 2, Icoil=-1A')

output_path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC.mph'
model.save(output_path)
print(f'Saved to {output_path}')
