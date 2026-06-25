import mph

client = mph.start(cores=6)

model = client.load(r'D:\COMSOL62\Multiphysics\applications\ACDC_Module\Devices,_Inductive\power_line_magnetic_field.mph')
jmodel = model.java

comp1 = jmodel.component('comp1')
geom = comp1.geom('geom1')

print('Space dim:', geom.getSDim())
print('Geom type:', geom.getType())

print('Geometry features:', geom.feature().tags())

mf = comp1.physics('mf')
print('MF features:', mf.feature().tags())
for ftag in mf.feature().tags():
    f = mf.feature(ftag)
    print(f'  {ftag}: type={f.type()}')
