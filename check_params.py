import mph

client = mph.start(cores=6)

path = r'C:\Users\nguye\comsol_multiphysics_mcp\comsol_models\2D_Coils\2D_Coils_ACDC_N300_freq.mph'
model = client.load(path)
jmodel = model.java

# Check global parameters
params = jmodel.param()
print('=== Global Parameters ===')
try:
    param_tags = list(params.tags())
    print(f'Number of parameters: {len(param_tags)}')
    for p in param_tags[:20]:
        try:
            expr = params.getString(p)
            desc = params.getDescription(p)
            print(f'  {p}: {expr}  ({desc})')
        except:
            print(f'  {p}: (error reading)')
except Exception as e:
    print(f'Error: {str(e)[:200]}')

# Check if there are unresolved parameters
print('\n=== Checking for unresolved references ===')
# Look at the coil features
comp1 = jmodel.component('comp1')
mf = comp1.physics('mf')
for tag in ['coil1', 'coil2']:
    c = mf.feature(tag)
    print(f'\n{tag} settings:')
    for prop in ['ICoil', 'N', 'Lfunction', 'T']:
        try:
            v = c.getStringArray(prop)
            print(f'  {prop}: {v}')
        except:
            pass
    
    # Check coil wire properties
    for prop in ['sigmaCoil', 'AreaFrom', 'coilWindDiameter', 'FillingFactor', 'coilWindArea']:
        try:
            v = c.getStringArray(prop)
            print(f'  {prop}: {v}')
        except:
            pass

# Check if the model needs geometry wire properties
print('\n=== Solving ===')
try:
    jmodel.study('std3').run()
    print('Solve succeeded!')
except Exception as e:
    print(f'Solve failed: {str(e)[:500]}')
