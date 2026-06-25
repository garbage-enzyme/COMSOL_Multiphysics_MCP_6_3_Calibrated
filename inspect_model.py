import mph

client = mph.start(cores=6)

model_path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_Complete.mph'
model = client.load(model_path)

jmodel = model.java

geom = jmodel.geom('geom1')
print('Geometry features:', geom.feature().tags())
geom.run()
doms = geom.getNDomains()
print(f'Number of domains: {doms}')

mat = jmodel.material('mat1')
print(f'Material label: {mat.label()}')
print(f'Selection: {mat.selection().get()}')

model.save()
print('Done')
