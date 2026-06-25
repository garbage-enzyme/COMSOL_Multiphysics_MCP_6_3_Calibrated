import mph

client = mph.start(cores=6)

model_path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC.mph'
model = client.load(model_path)

jmodel = model.java

# Check physics
print('Physics interfaces:')
for tag in jmodel.component('comp1').physics().tags():
    p = jmodel.component('comp1').physics(tag)
    print(f'  {tag}: {p.label()}')

# Check features of mf
if 'mf' in jmodel.component('comp1').physics().tags():
    mf = jmodel.component('comp1').physics('mf')
    print(f'mf features: {mf.feature().tags()}')
    for ftag in mf.feature().tags():
        f = mf.feature(ftag)
        print(f'  {ftag}:')
        try:
            print(f'    Icoil = {f.get("Icoil")}')
        except:
            print(f'    No Icoil property')
        try:
            sel = f.selection().get()
            print(f'    selection = {sel}')
        except:
            print(f'    No selection')

# Check materials
mat = jmodel.material('mat1')
print(f'\nMaterial: {mat.label()}')
print(f'  Selection: {mat.selection().get()}')

# Show model tree
print('\nFull model structure:')
model.print()

model.save()
print('\nDone.')
