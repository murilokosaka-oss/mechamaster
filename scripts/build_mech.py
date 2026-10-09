"""Build NOMAD MK.07: a fully modeled, textured, articulated expedition mech."""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / 'public' / 'textures'
ASSETS = ROOT / 'public' / 'models'
ART = ROOT / 'artifacts'
ASSETS.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.materials:
    bpy.data.materials.remove(block)

def material(name, surface=None, color=None, metal=0, rough=.4, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    if color:
        p.inputs['Base Color'].default_value = (*color, 1)
    if surface:
        n = m.node_tree.nodes
        l = m.node_tree.links
        c = n.new('ShaderNodeTexImage')
        c.image = bpy.data.images.load(str(TEX / f'{surface}-color.jpg'), check_existing=True)
        l.new(c.outputs['Color'], p.inputs['Base Color'])
        orm = n.new('ShaderNodeTexImage')
        orm.image = bpy.data.images.load(str(TEX / f'{surface}-orm.png'), check_existing=True)
        orm.image.colorspace_settings.name = 'Non-Color'
        sep = n.new('ShaderNodeSeparateColor')
        l.new(orm.outputs['Color'], sep.inputs['Color'])
        l.new(sep.outputs['Green'], p.inputs['Roughness'])
        l.new(sep.outputs['Blue'], p.inputs['Metallic'])
        normal = n.new('ShaderNodeTexImage')
        normal.image = bpy.data.images.load(str(TEX / 'surface-normal.png'), check_existing=True)
        normal.image.colorspace_settings.name = 'Non-Color'
        node = n.new('ShaderNodeNormalMap')
        node.inputs['Strength'].default_value = .22
        l.new(normal.outputs['Color'], node.inputs['Color'])
        l.new(node.outputs['Normal'], p.inputs['Normal'])
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = 3.5
    return m

armor = material('01 · weathered ceramic green / ceramic coating', 'ceramic')
dark = material('02 · graphite titanium chassis', 'dark')
steel = material('03 · brushed actuator steel', 'steel')
orange = material('04 · expedition ochre / safety enamel', 'ochre')
rubber = material('05 · carbon rubber / seals & hoses', 'rubber')
black = material('06 · recessed cavities', color=(.005, .008, .009), rough=.85)
ivory = material('07 · stencil ink', color=(.73, .76, .69), rough=.7)
optic = material('08 · amber optic phosphor', color=(1, .24, .025), metal=.2, rough=.17, emission=(1, .19, .015))
blue = material('09 · diagnostic LEDs', color=(.03, .7, .9), rough=.15, emission=(.02, .6, .95))
lens = material('10 · smoked optical glass', color=(.008, .06, .066), metal=.5, rough=.12)
for paint in (armor, orange):
    shader=paint.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Coat Weight'].default_value=.18
    shader.inputs['Coat Roughness'].default_value=.28

root = bpy.data.objects.new('NOMAD MK.07 · Expedition chassis', None)
bpy.context.collection.objects.link(root)
parts = {}
current = root

def assembly(name):
    global current
    g = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(g)
    g.parent = root
    current = g
    parts[name] = g
    return g

def finish(o, name, mat, bevel=0):
    o.name = name
    o.data.materials.append(mat)
    if bevel:
        o.data.materials.append(steel)
        b = o.modifiers.new('Machined edge chamfer', 'BEVEL')
        b.width = bevel
        b.segments = 3
        b.material = 1
        b.affect = 'EDGES'
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=b.name)
    for f in o.data.polygons:
        f.use_smooth = True
    if o.type == 'MESH':
        w = o.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
        w.keep_sharp = True
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=w.name)
    o.parent = current
    return o

def box(name, loc, dim, mat=armor, bevel=.04, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot: o.rotation_euler = rot
    return finish(o, name, mat, bevel)

def cylinder(name, loc, radius, depth, mat=steel, axis='Z', vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    if axis == 'X': o.rotation_euler[1] = math.pi / 2
    if axis == 'Y': o.rotation_euler[0] = math.pi / 2
    return finish(o, name, mat, min(radius * .11, .025))

def rod(name, a, b, radius, mat=steel, vertices=16):
    a, b = Vector(a), Vector(b)
    o = cylinder(name, (a + b) / 2, radius, (b-a).length, mat, vertices=vertices)
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return o

def hose(name, points, radius=.055, mat=rubber):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 12
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(points)-1)
    for bp, point in zip(sp.bezier_points, points):
        bp.co = point
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    o.parent = current
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o.select_set(False)
    return o

def torus(name, loc, major, minor, mat=rubber, axis='Z'):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=40, minor_segments=8, location=loc)
    o=bpy.context.object
    if axis == 'X': o.rotation_euler[1]=math.pi/2
    if axis == 'Y': o.rotation_euler[0]=math.pi/2
    return finish(o, name, mat)

def panel(name, loc, width, height, depth, mat=armor, taper=.16, rot=None):
    # Chamfered silhouette, eight corners on both faces; real inset depth.
    w, h = width/2, height/2
    t = min(width,height) * taper
    outline=[(-w+t,-h),(w-t,-h),(w,-h+t),(w,h-t),(w-t,h),(-w+t,h),(-w,h-t),(-w,-h+t)]
    vertices=[(x,y,z) for y in (-depth/2,depth/2) for x,z in outline]
    faces=[tuple(range(7,-1,-1)), tuple(range(8,16))]
    faces += [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=loc
    if rot: o.rotation_euler=rot
    # Box projection keeps texture scale tied to physical surface area.
    uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        n=p.normal
        for li in p.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co
            if abs(n.y) > .5: coord=(v.x,v.z)
            elif abs(n.x) > .5: coord=(v.y,v.z)
            else: coord=(v.x,v.y)
            uv.data[li].uv=(coord[0]*.8,coord[1]*.8)
    return finish(o,name,mat,.025)

def bolts(x, y, z, width, height):
    for dx in (-width/2,width/2):
        for dz in (-height/2,height/2):
            cylinder('Captive titanium fastener', (x+dx,y,z+dz), .041,.023,steel,'Y',6)
            cylinder('Fastener center recess', (x+dx,y-.014,z+dz), .014,.006,black,'Y',6)

def label(text, loc, size=.16, mat=ivory):
    cu=bpy.data.curves.new('Stencil · '+text,'FONT')
    cu.body=text
    cu.size=size
    cu.extrude=.0008
    cu.space_character=1.15
    cu.align_x='CENTER'
    o=bpy.data.objects.new('Stencil · '+text,cu)
    bpy.context.collection.objects.link(o)
    o.location=loc
    o.rotation_euler=(math.pi/2,0,0)
    o.data.materials.append(mat)
    o.parent=current
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH')
    o.select_set(False)

# Feet: segmented toes, soles, exposed ankle drive and foot suspension.
for s in (-1,1):
    x=s*.86
    assembly('Leg · '+('port' if s<0 else 'starboard'))
    box('Carbon tread sole',(x,-.35,.19),(1.16,1.87,.3),rubber,.07)
    panel('Cast armored foot',(x,-.3,.49),1.16,.48,1.5,dark)
    for i in range(3):
        tx=x+(i-1)*.34
        box('Independent toe armor',(tx,-1.04,.47),(.31,.48,.39),armor,.045)
        box('Toe wear lip',(tx,-1.29,.37),(.29,.055,.095),steel,.009)
    for i in range(7):
        box('Sole lug',(x,-1.12+i*.25,.1),(1.18,.12,.14),rubber,.018)
    cylinder('Ankle trunnion',(x,.07,.88),.25,1.18,dark,'X')
    for side in (-1,1):
        cylinder('Ankle end cap',(x+side*.59,.07,.88),.19,.07,steel,'X')
        rod('Ankle support strut',(x+side*.38,-.64,.56),(x+side*.31,-.03,1.37),.064)
        rod('Lower ankle piston',(x+side*.38,-.64,.56),(x+side*.34,-.31,1.02),.095,dark)
    box('Shin internal spine',(x,.12,1.84),(.52,.5,1.92),dark,.06)
    panel('Shin multilayer armor gasket',(x,-.31,1.9),.91,1.64,.48,rubber)
    panel('Shin chamfered armor',(x,-.54,1.99),.88,1.57,.27,armor)
    panel('Shin ochre insert',(x,-.704,1.71),.34,.91,.025,orange)
    box('Shin reinforcement ridge',(x,-.745,1.71),(.08,.05,.89),dark,.015)
    bolts(x,-.692,2.0,.65,1.21)
    label('07' if s<0 else 'R', (x,-.718,2.28),.23,dark)
    for i in range(4):
        box('Shin cooling slots',(x,.415,1.36+i*.17),(.47,.08,.055),black,.012)
    for side in (-1,1):
        rod('Shin piston chrome',(x+side*.37,.27,1.03),(x+side*.37,.27,2.77),.061)
        rod('Shin piston cylinder',(x+side*.37,.27,1.17),(x+side*.37,.27,2.04),.105,dark)
        torus('Cylinder retaining seal',(x+side*.37,.27,2.04),.096,.018,steel)
        hose('Hydraulic return line',[(x+side*.42,.26,2.62),(x+side*.56,.5,2.12),(x+side*.48,.44,1.13)],.041)
    cylinder('Knee drive',(x,0,2.97),.38,1.04,dark,'X')
    for side in (-1,1):
        cylinder('Knee circular casing',(x+side*.54,0,2.97),.31,.11,steel,'X')
        cylinder('Knee ochre hub',(x+side*.6,0,2.97),.19,.035,orange,'X')
        cylinder('Knee center lock',(x+side*.63,0,2.97),.08,.025,dark,'X',6)
    panel('Floating kneecap',(x,-.44,2.97),.98,.61,.36,orange)
    panel('Kneecap inset',(x,-.632,2.97),.65,.28,.02,dark)
    bolts(x,-.651,2.97,.76,.3)
    box('Thigh drive chassis',(x,.08,3.69),(.65,.63,1.13),dark,.08)
    panel('Upper leg armor',(x,-.36,3.69),.99,1.08,.41,armor)
    panel('Thigh inner gasket',(x,-.595,3.69),.67,.72,.055,dark)
    panel('Thigh service hatch',(x,-.634,3.69),.56,.58,.026,armor)
    bolts(x,-.655,3.69,.41,.41)
    for i in range(3):
        box('Thigh hatch vent',(x,-.661,3.61+i*.075),(.28,.012,.025),black,.003)
    rod('Thigh outer ram',(x+s*.47,.04,3.22),(x+s*.54,.17,4.24),.085,steel)
    rod('Thigh ram barrel',(x+s*.49,.09,3.52),(x+s*.54,.17,4.24),.14,dark)
    hose('Thigh feed hose',[(x+s*.46,.35,3.2),(x+s*.6,.52,3.7),(x+s*.42,.3,4.3)],.055)
    label('CAUTION', (x,-.589,4.03),.082,dark)

assembly('Pelvis & spinal articulation')
box('Pelvis chassis',(0,.05,4.39),(1.8,.86,.69),dark,.13)
panel('Pelvis apron',(0,-.48,4.37),1.12,.7,.27,armor)
panel('Pelvis amber inset',(0,-.636,4.41),.44,.3,.04,orange)
for s in (-1,1):
    cylinder('Hip bearing',(s*.87,.04,4.38),.35,.44,steel,'X')
    panel('Floating hip armor',(s*1.15,-.08,4.43),.57,.82,.66,armor,rot=(0,s*-.14,0))
    bolts(s*1.15,-.427,4.43,.29,.55)
for z,r in [(4.77,.53),(4.88,.49),(4.99,.48)]:
    cylinder('Segmented waist vertebra',(0,.12,z),r,.105,dark)
    torus('Waist pressure seal',(0,.12,z+.045),r,.03,rubber)
for s in (-1,1):
    rod('Diagonal waist actuator',(s*.5,-.32,4.59),(s*.79,-.18,5.15),.058)
    rod('Waist actuator shell',(s*.5,-.32,4.59),(s*.64,-.25,4.87),.092,dark)

assembly('Torso · monocoque armor')
box('Chest pressure vessel',(0,.05,5.69),(2.1,1.03,1.43),dark,.18)
panel('Chest rubber isolation layer',(0,-.5,5.83),2.23,1.33,.19,rubber)
panel('Main breastplate',(0,-.67,5.91),2.2,1.22,.27,armor,taper=.21)
panel('Upper chest overlapping plate',(0,-.805,6.21),1.9,.47,.12,armor,taper=.2)
panel('Central recessed instrument plate',(0,-.825,5.75),.7,.61,.045,dark)
panel('Reactor inspection window',(0,-.856,5.76),.35,.31,.03,lens)
for i in range(3):
    box('Core status strip',(-.09+i*.09,-.882,5.76),(.025,.011,.14),blue,.005)
bolts(0,-.82,5.94,1.83,.77)
for s in (-1,1):
    for i in range(4):
        box('Breastplate intake grille',(s*.67,-.824,5.59+i*.1),(.35,.03,.034),black,.006)
    panel('Side chest sloped armor',(s*1.04,.03,5.7),.43,1.1,.97,armor,rot=(0,s*.12,0))
    rod('Chest external rail',(s*1.035,-.66,5.38),(s*1.035,-.66,6.38),.034,steel)
    panel('Lower chest skirt',(s*.57,-.53,5.15),.8,.37,.4,dark,rot=(0,s*.09,0))
label('N O M A D',(0,-.878,6.18),.155,dark)
label('MK.07',(-.64,-.838,5.85),.145,dark)
label('FIELD SYSTEMS',(.66,-.84,5.89),.065,dark)
for i in range(7):
    box('Serial data strokes',(.5+i*.034,-.839,5.78),(.012,.008,.045+(.035 if i%2 else 0)),dark,.001)

assembly('Backpack · thermal & power systems')
box('Power module main',(0,.82,5.75),(1.7,.65,1.46),dark,.12)
for s in (-1,1):
    box('Thermal radiator bank',(s*.58,1.18,5.7),(.52,.28,1.34),black,.035)
    for i in range(12):
        box('Heat dissipation fin',(s*.58,1.34,5.1+i*.1),(.53,.23,.036),steel,.008)
    cylinder('Power canister',(s*.92,.75,5.62),.18,1.36,dark)
    for z in (5.07,5.68,6.15): torus('Canister clamp',(s*.92,.75,z),.18,.034,steel)
    hose('Back power cable',[(s*.62,1.1,6.34),(s*1.08,1.15,6.17),(s*1.17,.76,5.51),(s*.9,.51,4.9)],.07)
    cylinder('Exhaust outlet',(s*.58,1.03,6.59),.13,.43,steel)
    cylinder('Exhaust bore',(s*.58,1.03,6.815),.093,.006,black)
box('Battery diagnostic cover',(0,1.18,5.75),(.37,.17,1.15),orange,.04)

# Shoulders and arms use concentric joints, armored covers and visible rams.
for s in (-1,1):
    assembly('Arm · '+('port' if s<0 else 'starboard'))
    cylinder('Shoulder spindle',(s*1.37,0,6.08),.36,.86,steel,'X')
    cylinder('Shoulder joint',(s*1.65,0,6.08),.44,.46,dark,'X')
    panel('Pauldron seal',(s*1.72,.02,6.4),1.2,.76,1.15,rubber)
    panel('Angular shoulder shell',(s*1.75,-.05,6.5),1.19,.68,1.22,armor)
    panel('Shoulder ochre identification',(s*1.75,-.675,6.49),.91,.34,.022,orange)
    bolts(s*1.75,-.686,6.49,.88,.36)
    label('07' if s<0 else 'NMD',(s*1.75,-.692,6.43),.21,dark)
    for i in range(5):
        box('Shoulder air inlet',(s*1.75,-.682,6.7),(.64,.018,.019),dark,.003)
    box('Upper arm core',(s*1.89,.02,5.64),(.48,.51,1.07),dark,.05)
    panel('Bicep armored shield',(s*1.98,-.28,5.64),.68,.89,.32,armor,rot=(0,s*.09,0))
    bolts(s*1.98,-.452,5.64,.42,.62)
    cylinder('Elbow axle',(s*2.03,0,4.97),.29,.86,dark,'X')
    cylinder('Elbow outer ring',(s*2.47,0,4.97),.23,.085,steel,'X')
    cylinder('Elbow cap',(s*2.52,0,4.97),.13,.04,orange,'X')
    panel('Elbow protector',(s*2.03,-.3,4.97),.61,.42,.22,dark)
    rod('Upper arm piston',(s*2.19,.14,5.9),(s*2.31,.07,4.88),.065,steel)
    rod('Upper arm piston sleeve',(s*2.19,.14,5.9),(s*2.25,.105,5.4),.112,dark)
    hose('Shoulder armored hose',[(s*1.35,.43,6.28),(s*1.83,.69,6.1),(s*2.2,.61,5.52),(s*2.12,.33,4.87)],.07)
    box('Forearm exoskeleton',(s*2.12,-.09,4.29),(.64,.64,1.04),dark,.07)
    panel('Forearm isolation pad',(s*2.12,-.43,4.3),.87,1.08,.23,rubber)
    panel('Forearm armor shell',(s*2.12,-.59,4.3),.83,1.01,.19,armor)
    panel('Forearm tool cover',(s*2.12,-.699,4.37),.44,.58,.037,orange if s<0 else dark)
    bolts(s*2.12,-.702,4.3,.6,.76)
    for i in range(3):
        box('Forearm diagnostic slots',(s*2.12,-.732,4.43+i*.06),(.28,.012,.023),black,.004)
    rod('Forearm tension bar',(s*2.48,.01,3.83),(s*2.48,.01,4.71),.048,steel)
    cylinder('Wrist swivel',(s*2.12,-.06,3.68),.22,.25,steel)
    torus('Wrist seal',(s*2.12,-.06,3.69),.22,.025,rubber)
    box('Manipulator palm',(s*2.12,-.09,3.41),(.56,.52,.42),dark,.05)
    panel('Hand dorsal plate',(s*2.12,-.37,3.43),.52,.32,.06,armor)
    # Four fingers, two individual machined segments each, with hinge bearings.
    for i in range(4):
        fx=s*2.12+(i-1.5)*.132
        cylinder('Finger pivot',(fx,-.19,3.19),.053,.104,steel,'X',16)
        box('Finger proximal',(fx,-.2,3.06),(.105,.17,.24),dark,.02)
        box('Finger distal',(fx,-.265,2.91),(.1,.22,.14),steel,.018,rot=(.32,0,0))
        box('Finger rubber grip',(fx,-.385,2.92),(.08,.035,.09),rubber,.009)
    box('Opposable thumb',(s*2.47,-.11,3.26),(.18,.2,.31),dark,.025,rot=(0,s*-.5,0))
    box('Thumb end effector',(s*2.51,-.2,3.07),(.15,.22,.14),steel,.02)

assembly('Head · optical command module')
cylinder('Neck rotary coupling',(0,.035,6.57),.29,.37,steel)
for z in (6.45,6.55,6.65): torus('Neck flex ring',(0,.035,z),.29,.035,rubber)
panel('Helmet central shell',(0,-.03,7.01),1.02,.85,.83,armor,taper=.22)
panel('Helmet recessed face',(0,-.48,7.0),.88,.56,.1,dark,taper=.17)
panel('Visor pressure gasket',(0,-.548,7.09),.85,.23,.075,rubber,taper=.2)
panel('Single optical visor',(0,-.594,7.09),.77,.13,.032,lens,taper=.12)
for i in range(7):
    box('Amber sensor cell',((i-3)*.096,-.618,7.095),(.074,.014,.042),optic,.01)
panel('Armored brow',(0,-.562,7.27),1.0,.18,.15,armor,taper=.17)
panel('Helmet chin plate',(0,-.52,6.82),.68,.24,.14,armor)
for i in range(5):
    box('Vocoder grille',((i-2)*.075,-.602,6.84),(.033,.019,.1),black,.006)
for s in (-1,1):
    cylinder('Temple sensor turret',(s*.54,.025,7.04),.17,.13,dark,'X')
    cylinder('Temple ochre bearing',(s*.615,.025,7.04),.11,.025,orange,'X')
    panel('Cheek guard',(s*.42,-.4,6.92),.18,.32,.28,dark)
    cylinder('Helmet fastener',(s*.35,-.46,7.35),.033,.022,steel,'Y',6)
box('Crown identification stripe',(0,-.1,7.447),(.13,.43,.009),orange,.003)
label('N-07',(0,-.601,6.76),.07,dark)
rod('Antenna base',(.38,.27,7.23),(.38,.27,7.58),.037,dark)
rod('Radio antenna',(.38,.27,7.55),(.42,.29,8.08),.012,steel)
cylinder('Antenna tip',(.42,.29,8.08),.023,.025,rubber)

assembly('Auxiliary sensor systems')
rod('Shoulder beacon mast',(-1.69,.27,6.84),(-1.69,.27,7.17),.043,steel)
cylinder('Beacon housing',(-1.69,.27,7.21),.107,.17,dark)
cylinder('Amber beacon lens',(-1.69,.27,7.29),.085,.06,optic)
box('Survey camera housing',(1.68,-.05,6.97),(.38,.44,.25),dark,.035)
cylinder('Survey lens barrel',(1.68,-.31,6.97),.1,.11,steel,'Y')
cylinder('Survey coated lens',(1.68,-.37,6.97),.073,.013,lens,'Y')
for s in (-1,1):
    box('Chest work lamp surround',(s*.83,-.49,6.42),(.26,.23,.18),dark,.025)
    box('Chest work lamp lens',(s*.83,-.617,6.42),(.2,.014,.092),ivory,.015)

# Grounding, rig metadata, and clean GLB export include the model only.
bpy.ops.object.select_all(action='DESELECT')
mech_objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in [root, *parts.values(), *mech_objects]: o.select_set(True)
bpy.context.view_layer.objects.active=mech_objects[0]
bpy.ops.export_scene.gltf(filepath=str(ASSETS/'nomad-mk07.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT')
stats={'name':'NOMAD MK.07','height_m':8.1,'mesh_count':len(mech_objects),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in mech_objects),'materials':len(bpy.data.materials),'assemblies':list(parts.keys())}
(ASSETS/'manifest.json').write_text(json.dumps(stats,indent=2))

current=None
ground=material('Stage · worn concrete','ground')
box('Concrete cyclorama',(0,0,-.12),(2000,2000,.2),ground,.01)
import sys
sys.path.insert(0,str(ROOT/'scripts'))
from studio_backdrop import add_backdrop
add_backdrop(ground)
# Oversized physically correct studio emitters create broad metal reflections.
def area(name,loc,energy,color,size,target=(0,0,4),size_y=None):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.color=color
    data.shape='RECTANGLE'
    data.size=size
    data.size_y=size_y or size
    ob=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(ob)
    ob.location=loc
    ob.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
area('Key · warm overhead softbox',(2,-7,12),2600,(1,.83,.65),7, size_y=5)
area('Fill · cool stripbox',(-6,-3,7),1800,(.53,.72,1),5,size_y=8)
area('Rim · large neutral source',(4,4,9),3100,(.75,.85,1),5,size_y=7)
area('Low warm bounce',(-3,1,4),850,(1,.4,.12),3)
area('Front face fill',(1,-10,5),600,(1,.96,.88),4)
world=bpy.context.scene.world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.17,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.25
bpy.ops.object.camera_add(location=(10.1,-16.8,9.4))
cam=bpy.context.object
cam.name='Hero camera · 70 mm'
cam.rotation_euler=(Vector((0,-.05,4.05))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='PERSP'
cam.data.lens=58
scene=bpy.context.scene
scene.camera=cam
scene.render.engine='CYCLES'
scene.cycles.samples=256
# This cloud Blender build has no OpenImageDenoise. Preserve ray tracing
# and use enough native samples rather than requiring an unavailable denoiser.
scene.cycles.use_denoising=False
scene.cycles.max_bounces=8
scene.render.resolution_x=1400
scene.render.resolution_y=1400
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(ART/'nomad-hero.png')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'nomad-mk07.blend'))
print('NOMAD_STATS '+json.dumps(stats))
if '--render' in __import__('sys').argv:
    bpy.ops.render.render(write_still=True)
