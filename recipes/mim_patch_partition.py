"""
MIM patch: partition bnd6 into patch + rest.
LayeredTransition + LML only on patch boundary.
Rest = plain Al2O3/air interface (continuity).
"""
import mph, jpype, sys, time
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass

def jarr(v, d=jpype.JDouble): return jpype.JArray(d)(v)
def jarr_s(v): return jpype.JArray(jpype.JString)(v)
def jarr_i(v): return jpype.JArray(jpype.JInt)(v)

Px=0.6e-6; Py=0.6e-6; t_al2o3=30e-9; H_air=0.83e-6; t_au=30e-9
ax=0.3e-6; px0=(Px-ax)/2  # 0.15µm
au_drude_param = "1-(1.37e16)^2/((2*pi*c_const/wl)*((2*pi*c_const/wl)+i*4.1e13))"

client = mph.Client(cores=4, version='6.4')
print('Connected', client.version, flush=True)
m = client.create('MIM_patch'); jm = m.java
jm.param().set('wl', '5e-6[m]')

# Global Au material (Drude)
mat_au_g = jm.material().create('mat_au','Common')
mat_au_g.propertyGroup('def').set('relpermittivity', au_drude_param)
mat_au_g.propertyGroup('def').set('sigmabnd', '0')
mat_au_g.propertyGroup('def').set('murbnd', '1')
lm_au = jm.material().create('lm_au','LayeredMaterial')
lm_au.set('layername','Au'); lm_au.set('thickness', str(t_au)); lm_au.set('link','mat_au')
lm_au.propertyGroup('def').set('relpermittivity', au_drude_param)
lm_au.propertyGroup('def').set('sigmabnd', '0')
lm_au.propertyGroup('def').set('murbnd', '1')

# Component + geometry
comp = jm.component().create('comp1', True)
g = comp.geom().create('geom1', 3)
g.feature().create('b_al2','Block').set('size',jarr([Px,Py,t_al2o3]))
g.feature().create('b_air','Block').set('size',jarr([Px,Py,H_air])); g.feature('b_air').set('pos',jarr([0,0,t_al2o3]))
g.run()
print('Before partition: dom', g.getNDomains(), 'bnd', g.getNBoundaries(), flush=True)

# Partition bnd6 (interface) using WorkPlane (xy at z=t_al2o3) + Rectangle + PartitionFaces
wp = g.feature().create('wp1','WorkPlane')
wp.set('planetype', 'quick')
wp.set('quickplane', 'xy')
wp.set('quickz', str(t_al2o3))  # z offset to interface
wp.set('unite', True)
wpg = wp.geom()
r1 = wpg.feature().create('r1','Rectangle')
r1.set('pos', jarr([px0, px0])); r1.set('size', jarr([ax, ax]))
print('WorkPlane xy at z=', t_al2o3, 'rect', px0, ax, flush=True)
g.run()  # build workplane
print('After WP: dom', g.getNDomains(), 'bnd', g.getNBoundaries(), flush=True)

# PartitionFaces: partition bnd6 using rectangle from workplane
pf = g.feature().create('pf1','PartitionFaces')
# Use feature tags as object tags directly
print('Using b_air tag + wp1 tag for partition', flush=True)
try:
    pf.selection('face').set('b_air', jarr_i([6]))
    pf.selection('partition').set('wp1')
    g.run()
    print('After partition: dom', g.getNDomains(), 'bnd', g.getNBoundaries(), flush=True)
except Exception as e:
    print('Partition err:', repr(e)[:200], flush=True)
    try:
        pf.set('partitionobj', jarr_s(['wp1']))
        g.run()
        print('Partition alt: bnd', g.getNBoundaries(), flush=True)
    except Exception as e2:
        print('Partition alt err:', repr(e2)[:200], flush=True)

# Continue setup...
mat_al2 = comp.material().create('mat_al2','Common')
mat_al2.propertyGroup('def').set('relpermittivity','3.1'); mat_al2.selection().set([1])
mat_air = comp.material().create('mat_air','Common')
mat_air.propertyGroup('def').set('relpermittivity','1'); mat_air.selection().set([2])

# ewfd + PeriodicStructure
p = comp.physics().create('ewfd','ElectromagneticWavesFrequencyDomain', str(g.getSDim()))
ps = p.feature().create('ps1','PeriodicStructure',3)
p1b = list(ps.feature('pport1').selection().entities()); p2b = list(ps.feature('pport2').selection().entities())
ps.selection('excitedPortSelection').set(p1b)
print('pport1:', p1b, 'pport2:', p2b, flush=True)

# LayeredImpedance on bottom
lib = p.feature().create('lib1','LayeredImpedanceBoundaryCondition',2)
lib.selection().set(p2b)
lib.set('substrateMaterial','mat_au')
lib.set('DisplacementFieldModelSubstrate','RelativePermittivity')
lib.set('epsilonrImp_mat','userdef'); lib.set('epsilonrImp', au_drude_param); lib.set('allLayers', False)

# Find patch boundary (smallest boundary at z=t_al2o3)
# List all boundaries with center z≈t_al2o3
print('\nBoundaries at interface (z≈t_al2o3):', flush=True)
nb = g.getNBoundaries()
patch_bnd = None
for bn in range(1, nb+1):
    try:
        # Use geom eval to get center - try different API
        pass
    except Exception: pass
# For now, try all new boundaries except original ones
# Original: 11 bnd. After partition should have more.
# Patch is the rectangle area. Let's try bnd numbers > original.

# LML on patch boundary (try bnd 12 or similar - will need to identify)
# For now, try to find by evaluating boundary area
# The patch area = ax*ax = 0.09e-12, rest = Px*Py - patch = 0.27e-12
# Try setting LML on each new boundary and check

# Actually, let's use a Selection approach: box selection at patch center
# For now, just print boundary count and try bnd 12 (first new after partition)
patch_bnd = 12  # guess - will verify
print('Trying patch_bnd=', patch_bnd, flush=True)

# LML on patch boundary
lml_au = comp.material().create('lml_au','LayeredMaterialLink')
lml_au.set('link','lm_au')
lml_au.selection().all(); lml_au.selection().clear(); lml_au.selection().add([patch_bnd])
sh = lml_au.propertyGroup('shell')
sh.set('lth', str(t_au)); sh.set('relpermittivity', au_drude_param)
sh.set('sigmabnd', '0'); sh.set('murbnd', '1')

# LayeredTransition on patch boundary
ltr = p.feature().create('ltr1','LayeredTransitionBoundaryCondition',2)
ltr.selection().set([patch_bnd])
ltr.set('DisplacementFieldModel','RelativePermittivity')
for prop, val in [('sigmabnd_mat','userdef'),('sigmabnd','0'),('murbnd_mat','userdef'),('murbnd','1')]:
    try: ltr.set(prop, val)
    except Exception: pass
ltr.set('lth', str(t_au))
print('LTR on bnd', patch_bnd, 'lth=', ltr.getString('lth'), 'shelllist=', ltr.getString('shelllist'), flush=True)

# Mesh
mesh = comp.mesh().create('mesh1')
sz = mesh.feature().create('size1','Size')
sz.set('hmax', float(H_air/10)); sz.set('hmaxactive', True)
sz.set('hmin', float(t_al2o3/2)); sz.set('hminactive', True)
ftri = mesh.feature().create('ftri1','FreeTri'); ftri.selection().set(p2b)
sw = mesh.feature().create('sw1','Sweep'); sw.selection().set([1,2])
try:
    mesh.run(); print('Mesh:', mesh.getNumElem(), flush=True)
except Exception as e:
    print('Mesh FAIL:', repr(e)[:200], flush=True)

# Sweep
wls = [3e-6, 4e-6, 5e-6, 6e-6, 7e-6, 8e-6]
study = jm.study().create('std1'); study.create('step1','Wavelength')
step = study.feature('step1'); step.set('punit','m'); step.set('plist', str(5e-6))
study.create('sweep1','Parametric')
sweep = study.feature('sweep1'); sweep.set('pname','wl')
sweep.set('plist', ' '.join(str(w) for w in wls))
print('Sweeping', len(wls), 'wavelengths...', flush=True)
try:
    t0=time.time(); jm.study('std1').run(); t1=time.time()
    print(f'Solve OK {t1-t0:.2f}s', flush=True)
    R = m.evaluate('ewfd.Rtotal')
    for i, wl in enumerate(wls):
        Ri = float(R[i])
        print(f'  wl={wl*1e6:.1f}µm  R={Ri:.6f}  eps=1-R={1-Ri:.6f}', flush=True)
except Exception as e:
    print('Solve FAIL:', repr(e)[:300], flush=True)
    import traceback; traceback.print_exc()

try: m.save('C:/Users/陆星/AppData/Local/Temp/opencode/MIM_patch.mph')
except Exception as e: print('save err:', repr(e)[:150], flush=True)
try: client.disconnect()
except Exception: pass
print('Done.', flush=True)
