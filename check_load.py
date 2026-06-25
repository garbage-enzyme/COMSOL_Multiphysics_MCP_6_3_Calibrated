import mph
import jpype

client = mph.start(cores=1)

mu = jpype.JClass('com.comsol.model.util.ModelUtil')
clazz = mu.getClass()
for m in clazz.getDeclaredMethods():
    name = m.getName()
    if name == 'load':
        params = [p.getName() for p in m.getParameterTypes()]
        print(f'load({", ".join(params)})')
