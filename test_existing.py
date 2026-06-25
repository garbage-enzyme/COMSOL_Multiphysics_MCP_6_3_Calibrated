import mph

client = mph.start(cores=6)

model = client.load(r'D:\COMSOL62\Multiphysics\applications\ACDC_Module\Devices,_Inductive\power_line_magnetic_field.mph')
jmodel = model.java

comp_tags = list(jmodel.component().tags())
print('Component tags:', comp_tags)

for ct in comp_tags:
    comp = jmodel.component(ct)
    phys_tags = list(comp.physics().tags())
    print(f'  {ct} physics: {phys_tags}')
    for pt in phys_tags:
        p = comp.physics(pt)
        print(f'    {pt}: label={p.label()}, type={p.type()}')
        
        # Check features
        features = list(p.feature().tags())
        print(f'    features: {features}')
        
        # Check a feature's type
        for ft in features[:3]:
            f = p.feature(ft)
            print(f'      {ft}: type={f.type()}')
