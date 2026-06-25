"""Build EC-NDT COMSOL model by cloning an existing ACDC model."""
import mph
import numpy as np
from jpype import JClass

client = mph.Client(cores=4)
MU = JClass('com.comsol.model.util.ModelUtil')

# Load existing ACDC model to get product association
src = r'D:\COMSOL62\Multiphysics\applications\ACDC_Module\Devices,_Inductive\ecore_transformer.mph'
model = client.load(src)
model.rename('EC_NDT_Model')
jm = model.java

print(f'Products: {jm.getUsedProducts()}')

# Remove everything and rebuild
for p_name in list(model.physics()):
    (model / 'physics' / p_name).remove()

# Remove existing geometry and create fresh 2D geometry
jm.geom().remove('geom1')
geom = jm.geom().create('geom1', 2)

# Also remove existing materials, studies, mesh
for tag in list(jm.material().tags()):
    try:
        jm.material().remove(tag)
    except:
        pass

for tag in list(jm.study().tags()):
    try:
        jm.study().remove(tag)
    except:
        pass

for tag in list(jm.mesh().tags()):
    try:
        jm.mesh().remove(tag)
    except:
        pass

# Parameters
model.parameter('len_unit', '1[mm]')
model.description('len_unit', 'Length unit: mm')

# Build geometry (2D)
# Air domain: 80x80 mm centered at (0,0)
r1 = geom.create('r1', 'Rectangle')
r1.set('size', [80.0, 80.0])
r1.set('pos', [-40.0, -40.0])
r1.set('base', 'center')

# Right coil coil+: 2x10 mm centered at (6,0)
r2 = geom.create('r2', 'Rectangle')
r2.set('size', [2.0, 10.0])
r2.set('pos', [6.0, 0.0])
r2.set('base', 'center')

# Left coil coil-: 2x10 mm centered at (-6,0)
r3 = geom.create('r3', 'Rectangle')
r3.set('size', [2.0, 10.0])
r3.set('pos', [-6.0, 0.0])
r3.set('base', 'center')

# Steel specimen: 40x2 mm centered at (0,-7)
r4 = geom.create('r4', 'Rectangle')
r4.set('size', [40.0, 2.0])
r4.set('pos', [0.0, -7.0])
r4.set('base', 'center')

geom.run()
print('Geometry built')

# Materials (using 'Common' type)
mat_air = jm.material().create('mat1', 'Common')
mat_air.label('Air')
mat_air.selection().set([1])
mat_air.propertyGroup('def').set('relpermeability', '1')
mat_air.propertyGroup('def').set('electricconductivity', '0[S/m]')

mat_steel = jm.material().create('mat2', 'Common')
mat_steel.label('Steel specimen')
mat_steel.selection().set([2])
mat_steel.propertyGroup('def').set('relpermeability', '100')
mat_steel.propertyGroup('def').set('electricconductivity', '6.99e6[S/m]')

mat_copper = jm.material().create('mat3', 'Common')
mat_copper.label('Copper')
mat_copper.selection().set([3, 4])
mat_copper.propertyGroup('def').set('relpermeability', '1')
mat_copper.propertyGroup('def').set('electricconductivity', '6e7[S/m]')
print('Materials created')

# Physics: Magnetic Fields (Induction Currents)
physics = jm.physics().create('mf', 'InductionCurrents')
physics.label('Magnetic Fields')
print('Magnetic Fields physics added')

# Coil 1 (right coil, coil+): domain 4, +1 A, 300 turns
coil1 = physics.create('coil1', 'Coil')
coil1.selection().set([4])
coil1.set('CoilType', 'Multi-turn')
coil1.set('Icoil', '1[A]')
coil1.set('N', '300')
coil1.label('Coil 1 (Right)')

# Coil 2 (left coil, coil-): domain 3, -1 A, 300 turns
coil2 = physics.create('coil2', 'Coil')
coil2.selection().set([3])
coil2.set('CoilType', 'Multi-turn')
coil2.set('Icoil', '-1[A]')
coil2.set('N', '300')
coil2.label('Coil 2 (Left)')
print('Coils configured')

# Study: Coil Geometry Analysis + Stationary
study = jm.study().create('std1')
study.label('Study 1')

step1 = study.create('step1', 'CoilGeometryAnalysis')
step1.label('Coil Geometry Analysis')

step2 = study.create('step2', 'Stationary')
step2.label('Stationary')
print('Study created')

# Mesh
mesh1 = jm.mesh().create('mesh1')
mesh1.autoMeshSize(4)  # Fine mesh
mesh1.run()
print('Mesh generated')

# Solve
jm.study('std1').run()
print('Study solved')

# Evaluate magnetic flux density
B_norm = model.evaluate('mf.normB', 'T')
print(f'B_norm type: {type(B_norm)}')
B_array = np.atleast_1d(np.array(B_norm, dtype=float))
B_max = float(np.max(B_array))
B_mean = float(np.mean(B_array))
print(f'Bmax = {B_max:.10f} T')
print(f'Bmax = {B_max*1000:.3f} mT')
print(f'Mean |B| = {B_mean*1000:.3f} mT')

# Save
model.save(r'C:\Users\nguye\EC_NDT_Model.mph')
print('Model saved to C:\\Users\\nguye\\EC_NDT_Model.mph')
