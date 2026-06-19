import mph

client = mph.start(cores=6)

model_path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC.mph'
model = client.load(model_path)

jmodel = model.java

# Check physics interfaces
physics_tags = list(jmodel.component('comp1').physics().tags())
print('Physics interfaces:', physics_tags)

if 'mf' in physics_tags:
    mf = jmodel.component('comp1').physics('mf')
    print(f'mf label: {mf.label()}')
    print(f'mf features: {mf.feature().tags()}')
    
    for ftag in mf.feature().tags():
        f = mf.feature(ftag)
        print(f'\n  Feature: {ftag}')
        try:
            print(f'    Icoil = {f.get("Icoil")}')
        except:
            print(f'    No Icoil')
        try:
            print(f'    type = {f.get("CoilType")}')
        except:
            pass
        try:
            sel = list(f.selection().get())
            print(f'    selection = {sel}')
        except:
            print(f'    selection error')

print('\nDone.')
