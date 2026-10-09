"""A real curved cyclorama, giving the studio camera a seamless background."""
import bpy
import math

def add_backdrop(material):
    if bpy.data.objects.get('Studio · seamless curved backdrop'):
        return
    profile=[]
    for i in range(33):
        angle=i/32*math.pi/2
        profile.append((10+5*math.sin(angle),-.02+5*(1-math.cos(angle))))
    profile.append((15,40))
    vertices=[(x,y,z) for y,z in profile for x in (-60,60)]
    faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(profile)-1)]
    mesh=bpy.data.meshes.new('Continuous studio sweep')
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth=True
        for loop_index in polygon.loop_indices:
            v=mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv=(v.x*.01,(v.y+v.z)*.01)
    obj=bpy.data.objects.new('Studio · seamless curved backdrop',mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj
