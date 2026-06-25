"""Test ACDC physics and build model."""
import mph
from jpype import JClass

client = mph.Client(cores=4)
MU = JClass('com.comsol.model.util.ModelUtil')

print('ACDC product available:', MU.hasProduct('ACDC'))
print('License checkout:', MU.checkoutLicense('ACDC'))

# 1. Load an existing ACDC model
model_path = r'D:\COMSOL62\Multiphysics\applications\ACDC_Module\Applications\helmholtz_coil.mph'
model_existing = client.load(model_path)
print(f'\nLoaded: {model_existing.name()}')
jm_existing = model_existing.java
print(f'Used products: {jm_existing.getUsedProducts()}')
print(f'Physics: {model_existing.physics()}')

# Check what physics type is used
for p in model_existing.physics():
    phys_node = model_existing / 'physics' / p
    print(f'  Physics node tag: {phys_node.tag()}')
    print(f'  Physics type: {phys_node.java.type()}')

# 2. Now remove this model and try to replicate
client.remove(model_existing)
print('\nRemoved existing model')

# 3. Create a fresh model the same way but with our geometry
model = client.create('EC_NDT_Model')
jm = model.java
print(f'Used products: {jm.getUsedProducts()}')

# 4. Build geometry  
geom = jm.geom().create('geom1', 2)
r1 = geom.create('r1', 'Rectangle')
r1.set('size', [80, 80])
r1.set('pos', [-40, -40])
r1.set('base', 'center')
r2 = geom.create('r2', 'Rectangle')
r2.set('size', [2, 10])
r2.set('pos', [6, 0])
r2.set('base', 'center')
r3 = geom.create('r3', 'Rectangle')
r3.set('size', [2, 10])
r3.set('pos', [-6, 0])
r3.set('base', 'center')
r4 = geom.create('r4', 'Rectangle')
r4.set('size', [40, 2])
r4.set('pos', [0, -7])
r4.set('base', 'center')
geom.run()
print('\nGeometry built')

# 5. Try physics with InductionCurrents  
try:
    p = jm.physics().create('mf', 'InductionCurrents')
    print('Physics (InductionCurrents) created!')
except Exception as e:
    print(f'Physics InductionCurrents: {str(e)[:200]}')
    print(f'Used products: {jm.getUsedProducts()}')

# Also try 'MagneticFields' which is what helmholtz_coil likely uses
try:
    p2 = jm.physics().create('mf2', 'MagneticFields')
    print('Physics (MagneticFields) created!')
except Exception as e:
    print(f'Physics MagneticFields: {str(e)[:200]}')

# Check if there's a physics named differently in the existing model
# Check the model library for the correct physics type name
print('\nDone')
