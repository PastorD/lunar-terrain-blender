"""Cycles node implementation of a single-Sun Hapke 2HG rough-surface approximation.

The angular BRDF is represented as a view-dependent Diffuse-BSDF weight, not
emission, so actual ray-traced occlusion is preserved. This is not a custom
general-purpose path-tracer closure; see README for its direct-light limits.
"""
import bpy,math

SCHEMA=2
SURFACE_SCHEMA=4
from .photometric_math import DEFAULTS, kernel, analytic

def build_group(sun):
    g=bpy.data.node_groups.new('HAPKE • direct solar reflectance','ShaderNodeTree')
    def socket(n,t,v=None,minv=None,maxv=None,desc=''):
        s=g.interface.new_socket(name=n,in_out='INPUT',socket_type=t)
        if v is not None: s.default_value=v
        if minv is not None: s.min_value=minv
        if maxv is not None: s.max_value=maxv
        s.description=desc
    socket('Normal','NodeSocketVector',(0,0,1))
    socket('Tint','NodeSocketColor',(.94,.93,.92,1))
    bounds={'w':(.001,.99),'b':(0,.95),'c':(-1,1),'B_SH0':(0,5),'h_SH':(.0001,1),'B_CB0':(0,2),'h_CB':(.0001,1),'theta':(0,45)}
    for name,v in DEFAULTS.items():socket(name,'NodeSocketFloat',v,*bounds[name])
    socket('Opposition strength','NodeSocketFloat',1,0,1,'0 disables both SHOE and CBOE; 1 enables them.')
    g.interface.new_socket(name='BSDF',in_out='OUTPUT',socket_type='NodeSocketShader')
    g.interface.new_socket(name='Phase radians',in_out='OUTPUT',socket_type='NodeSocketFloat')
    nodes,links=g.nodes,g.links
    inp=nodes.new('NodeGroupInput'); inp.location=(-1250,350)
    out=nodes.new('NodeGroupOutput'); out.location=(9000,300)
    geom=nodes.new('ShaderNodeNewGeometry'); geom.location=(-1250,-250)
    index=0
    def m(op,a,b=None,label=''):
        nonlocal index
        n=nodes.new('ShaderNodeMath');n.operation=op;n.label=label or op
        n.location=(-850+(index//12)*250,550-(index%12)*110);index+=1
        for i,v in enumerate([a,b]):
            if v is None:continue
            if isinstance(v,(int,float)):n.inputs[i].default_value=v
            else:links.new(v,n.inputs[i])
        return n.outputs[0]
    def vecdot(a,b,label):
        n=nodes.new('ShaderNodeVectorMath');n.operation='DOT_PRODUCT';n.label=label
        n.location=(-1100,-350-len([x for x in nodes if x.bl_idname=='ShaderNodeVectorMath'])*140)
        links.new(a,n.inputs[0]);links.new(b,n.inputs[1]);return n.outputs['Value']
    s=nodes.new('ShaderNodeCombineXYZ');s.name='SUN_DIRECTION';s.label='Actual Sun rotation → surface-to-Sun vector';s.location=(-1500,-650)
    expressions=['cos(rx)*sin(ry)*cos(rz)+sin(rx)*sin(rz)',
                 'cos(rx)*sin(ry)*sin(rz)-sin(rx)*cos(rz)',
                 'cos(rx)*cos(ry)']
    for j,expr in enumerate(expressions):
        dr=s.inputs[j].driver_add('default_value').driver;dr.expression=expr
        for name,axis in [('rx','ROT_X'),('ry','ROT_Y'),('rz','ROT_Z')]:
            v=dr.variables.new();v.name=name;v.type='TRANSFORMS'
            v.targets[0].id=sun;v.targets[0].transform_type=axis;v.targets[0].transform_space='WORLD_SPACE'
    io=inp.outputs
    mu0=vecdot(io['Normal'],s.outputs[0],'cos incidence')
    mu=vecdot(io['Normal'],geom.outputs['Incoming'],'cos emergence')
    cosalpha=vecdot(s.outputs[0],geom.outputs['Incoming'],'cos phase')
    alpha=m('ARCCOSINE',m('MAXIMUM',-1,m('MINIMUM',1,cosalpha)))
    weight=kernel(m,mu0,mu,cosalpha,io,io['Opposition strength'])
    tint=nodes.new('ShaderNodeVectorMath');tint.operation='SCALE';tint.location=(8500,500)
    links.new(io['Tint'],tint.inputs[0]);links.new(weight,tint.inputs['Scale'])
    diffuse=nodes.new('ShaderNodeBsdfDiffuse');diffuse.location=(8750,350)
    diffuse.inputs['Roughness'].default_value=0
    links.new(tint.outputs['Vector'],diffuse.inputs['Color']);links.new(io['Normal'],diffuse.inputs['Normal'])
    links.new(diffuse.outputs[0],out.inputs['BSDF']);links.new(alpha,out.inputs['Phase radians'])
    g['hapke_schema']=SCHEMA
    g['equation']='pi*f=w/4*mu0e/(mu0e+mue)*((1+Bsh)*P2HG+H(mu0e)*H(mue)-1)*(1+Bcb)*S/mu0; K=1'
    g['roughness_model']='Hapke effective angles and shadowing; theta describes unresolved slopes.'
    g['source']='Sato et al. 2014 appendix A; WAC_HAPKEPARAMMAP_566NM v1.1; c in [-1,1], positive backward.'
    return g

def material(group,name,rock=False,existing=None):
    mat=existing if existing is not None else bpy.data.materials.new(name);mat.diffuse_color=(.22,.21,.20,1)
    n,l=mat.node_tree.nodes,mat.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');out.location=(720,130)
    h=n.new('ShaderNodeGroup');h.node_tree=group;h.location=(400,100);h.name='HAPKE_CONTROLS'
    coord=n.new('ShaderNodeTexCoord');coord.location=(-1100,0)
    noise=n.new('ShaderNodeTexNoise');noise.location=(-850,200)
    noise.inputs['Scale'].default_value=.45 if rock else .035
    noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.75
    l.new(coord.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.location=(-550,220);ramp.name='REGOLITH_TINT'
    ramp.color_ramp.elements[0].position=.12;ramp.color_ramp.elements[0].color=(.84,.84,.84,1)
    ramp.color_ramp.elements[1].position=.83;ramp.color_ramp.elements[1].color=(1.06,1.06,1.06,1)
    l.new(noise.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],h.inputs['Tint'])
    medium=n.new('ShaderNodeTexNoise');medium.location=(-850,-80)
    medium.inputs['Scale'].default_value=9 if rock else 10
    medium.inputs['Detail'].default_value=4;medium.inputs['Roughness'].default_value=.8
    l.new(coord.outputs['Object'],medium.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.name='METRIC_RELIEF';bump.location=(-260,-80)
    bump.inputs['Strength'].default_value=.33 if rock else .5
    bump.inputs['Distance'].default_value=.022 if rock else .012
    l.new(medium.outputs['Fac'],bump.inputs['Height'])
    grain=n.new('ShaderNodeTexNoise');grain.location=(-550,-400)
    grain.inputs['Scale'].default_value=155 if rock else 220
    grain.inputs['Detail'].default_value=2
    l.new(coord.outputs['Object'],grain.inputs['Vector'])
    bump2=n.new('ShaderNodeBump');bump2.name='METRIC_GRAIN';bump2.location=(30,-90)
    bump2.inputs['Strength'].default_value=.28;bump2.inputs['Distance'].default_value=.0007
    l.new(grain.outputs['Fac'],bump2.inputs['Height']);l.new(bump.outputs['Normal'],bump2.inputs['Normal'])

    pits=n.new('ShaderNodeTexVoronoi');pits.location=(-850,-1250)
    pits.inputs['Scale'].default_value=20 if not rock else 32
    l.new(coord.outputs['Object'],pits.inputs['Vector'])
    profile=n.new('ShaderNodeMapRange');profile.location=(-570,-1250)
    profile.clamp=True;profile.interpolation_type='SMOOTHERSTEP'
    profile.inputs['From Min'].default_value=0;profile.inputs['From Max'].default_value=.30
    profile.inputs['To Min'].default_value=-1;profile.inputs['To Max'].default_value=0
    l.new(pits.outputs['Distance'],profile.inputs['Value'])
    pitbump=n.new('ShaderNodeBump');pitbump.name='METRIC_PITS';pitbump.location=(-30,-400)
    pitbump.inputs['Distance'].default_value=.0045 if not rock else .004
    l.new(profile.outputs['Result'],pitbump.inputs['Height'])
    l.new(bump.outputs['Normal'],pitbump.inputs['Normal'])
    l.new(pitbump.outputs['Normal'],bump2.inputs['Normal'])
    if rock:
        # Grain and small pits use world metres, so scaling a boulder does not
        # turn its grain into cobbles. Fractures use object space to fit its body.
        metric=n.new('ShaderNodeNewGeometry');metric.location=(-1400,-1100)
        for texture in (medium,grain,pits):l.new(metric.outputs['Position'],texture.inputs['Vector'])
        medium.inputs['Scale'].default_value=65
        bump.inputs['Distance'].default_value=.008
        grain.inputs['Scale'].default_value=280
        bump2.inputs['Distance'].default_value=.0012
        pits.inputs['Scale'].default_value=38
        pitbump.inputs['Distance'].default_value=.002
        warp=n.new('ShaderNodeTexNoise');warp.location=(-1450,-1550)
        warp.inputs['Scale'].default_value=3.7;warp.inputs['Detail'].default_value=3
        l.new(coord.outputs['Object'],warp.inputs['Vector'])
        offset=n.new('ShaderNodeVectorMath');offset.operation='SCALE';offset.location=(-1180,-1550)
        offset.inputs['Scale'].default_value=.18;l.new(warp.outputs['Color'],offset.inputs[0])
        warped=n.new('ShaderNodeVectorMath');warped.operation='ADD';warped.location=(-950,-1580)
        l.new(coord.outputs['Object'],warped.inputs[0]);l.new(offset.outputs['Vector'],warped.inputs[1])
        cracks=n.new('ShaderNodeTexVoronoi');cracks.feature='DISTANCE_TO_EDGE';cracks.location=(-720,-1580)
        cracks.name='ROCK_FRACTURE_NETWORK';cracks.inputs['Scale'].default_value=3.2
        l.new(warped.outputs['Vector'],cracks.inputs['Vector'])
        edge=n.new('ShaderNodeMapRange');edge.clamp=True;edge.interpolation_type='SMOOTHERSTEP';edge.location=(-470,-1640)
        edge.inputs['From Min'].default_value=0;edge.inputs['From Max'].default_value=.022
        edge.inputs['To Min'].default_value=1;edge.inputs['To Max'].default_value=0
        l.new(cracks.outputs['Distance'],edge.inputs['Value'])
        broken=n.new('ShaderNodeMapRange');broken.clamp=True;broken.interpolation_type='SMOOTHERSTEP';broken.location=(-450,-1860)
        broken.inputs['From Min'].default_value=.40;broken.inputs['From Max'].default_value=.65
        l.new(warp.outputs['Fac'],broken.inputs['Value'])
        mask=n.new('ShaderNodeMath');mask.operation='MULTIPLY';mask.location=(-190,-1720)
        l.new(edge.outputs['Result'],mask.inputs[0]);l.new(broken.outputs['Result'],mask.inputs[1])
        crack_bump=n.new('ShaderNodeBump');crack_bump.location=(180,-680);crack_bump.invert=True
        crack_bump.name='ROCK_FRACTURE_RELIEF';crack_bump.inputs['Distance'].default_value=.005
        l.new(mask.outputs[0],crack_bump.inputs['Height']);l.new(bump2.outputs['Normal'],crack_bump.inputs['Normal'])
        # Restrained darkening inside fractures; retain the same lunar BRDF.
        shade=n.new('ShaderNodeMath');shade.operation='MULTIPLY_ADD';shade.location=(30,-1660)
        l.new(mask.outputs[0],shade.inputs[0]);shade.inputs[1].default_value=-.28;shade.inputs[2].default_value=1
        tint=n.new('ShaderNodeVectorMath');tint.operation='SCALE';tint.location=(240,320)
        l.new(ramp.outputs['Color'],tint.inputs[0]);l.new(shade.outputs[0],tint.inputs['Scale'])
        l.new(tint.outputs['Vector'],h.inputs['Tint'])
        mineral=n.new('ShaderNodeTexNoise');mineral.name='ROCK_MINERAL_GRAIN';mineral.location=(-1000,-2240)
        mineral.inputs['Scale'].default_value=115;mineral.inputs['Detail'].default_value=2.5
        l.new(metric.outputs['Position'],mineral.inputs['Vector'])
        flecks=n.new('ShaderNodeMapRange');flecks.clamp=True;flecks.interpolation_type='SMOOTHERSTEP';flecks.location=(-730,-2240)
        flecks.inputs['From Min'].default_value=.30;flecks.inputs['From Max'].default_value=.70
        flecks.inputs['To Min'].default_value=.70;flecks.inputs['To Max'].default_value=1.24
        l.new(mineral.outputs['Fac'],flecks.inputs['Value'])
        mineral_tint=n.new('ShaderNodeVectorMath');mineral_tint.operation='SCALE';mineral_tint.location=(440,320)
        l.new(tint.outputs['Vector'],mineral_tint.inputs[0]);l.new(flecks.outputs['Result'],mineral_tint.inputs['Scale'])
        l.new(mineral_tint.outputs['Vector'],h.inputs['Tint'])
    # Remove subpixel procedural bump at range, using the active camera pixel size.
    cam=n.new('ShaderNodeCameraData');cam.location=(-1100,-650)
    pixel=n.new('ShaderNodeMath');pixel.operation='MULTIPLY';pixel.location=(-830,-650)
    l.new(cam.outputs['View Distance'],pixel.inputs[0])
    dr=pixel.inputs[1].driver_add('default_value').driver
    dr.expression='sensor/max(lens*width*percent/100,1)'
    for nm,path in [('sensor','camera.data.sensor_width'),('lens','camera.data.lens'),('width','render.resolution_x'),('percent','render.resolution_percentage')]:
        var=dr.variables.new();var.name=nm;var.type='SINGLE_PROP';var.targets[0].id_type='SCENE';var.targets[0].id=bpy.context.scene;var.targets[0].data_path=path
    for target,low,high,strength,yy in [(bump,.03,.25,.60 if rock else .50,-820),(bump2,.001,.008,.45 if rock else .22,-1050),(pitbump,.004,.025,.45,-1430)]:
        fade=n.new('ShaderNodeMapRange');fade.location=(-530,yy);fade.clamp=True;fade.interpolation_type='SMOOTHERSTEP'
        fade.label='Fade unresolved bump by projected pixel footprint'
        l.new(pixel.outputs[0],fade.inputs['Value']);fade.inputs['From Min'].default_value=low;fade.inputs['From Max'].default_value=high
        fade.inputs['To Min'].default_value=strength;fade.inputs['To Max'].default_value=0
        l.new(fade.outputs['Result'],target.inputs['Strength'])
    if rock:
        fade=n.new('ShaderNodeMapRange');fade.clamp=True;fade.interpolation_type='SMOOTHERSTEP'
        fade.location=(0,-2050);fade.label='Fade subpixel rock fractures'
        l.new(pixel.outputs[0],fade.inputs['Value'])
        fade.inputs['From Min'].default_value=.002;fade.inputs['From Max'].default_value=.022
        fade.inputs['To Min'].default_value=.65;fade.inputs['To Max'].default_value=0
        l.new(fade.outputs['Result'],crack_bump.inputs['Strength'])
    l.new((crack_bump if rock else bump2).outputs['Normal'],h.inputs['Normal']);l.new(h.outputs['BSDF'],out.inputs['Surface'])
    mat['Model']='Hapke 2HG rough-surface direct-Sun approximation; K=1; real cast shadows'
    mat['hapke_schema']=SCHEMA;mat['surface_schema']=SURFACE_SCHEMA;mat['lunar_rock']=rock
    return mat


def set_controls(mat,cfg):
    h=mat.node_tree.nodes.get('HAPKE_CONTROLS')
    if h is None:return
    rock=bool(mat.get('lunar_rock',False))
    from .appearance import PARAMETER_FIELDS
    for socket,field in dict(PARAMETER_FIELDS,**{'Opposition strength':'opposition'}).items():
        value=getattr(cfg,field)
        if socket=='w' and rock:value=min(.95,value*cfg.rock_albedo_ratio)
        h.inputs[socket].default_value=value
    ramp=mat.node_tree.nodes.get('REGOLITH_TINT')
    if ramp:
        for el,scale in zip(ramp.color_ramp.elements,(1-cfg.albedo_variation,1+cfg.albedo_variation)):
            el.color=tuple(float(v)*scale for v in cfg.soil_tint)+(1.,)
    if not rock:
        gain=getattr(cfg,'regolith_relief',1.)
        for name,base in [('METRIC_RELIEF',.012),('METRIC_GRAIN',.0007),('METRIC_PITS',.0045)]:
            node=mat.node_tree.nodes.get(name)
            if node:node.inputs['Distance'].default_value=base*gain
    mat['appearance']=cfg.appearance
    mat['parameter_provenance']='LROC regional 566 nm prior plus display appearance settings; not a calibrated fit to the supplied photographs.'
