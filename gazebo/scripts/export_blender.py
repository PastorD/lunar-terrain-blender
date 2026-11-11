"""Blender 5.2: blender -b --python export_blender.py -- source.blend output_dir.
Surface-schema exporter for Lunar Terrain; does not overwrite the input blend.
"""
import argparse, hashlib, json, math, os, sys, time
from pathlib import Path
import xml.etree.ElementTree as E
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

def log(*x): print(*x, flush=True)

def arrays(me):
    me.calc_loop_triangles()
    v=np.empty((len(me.vertices),3),np.float32); n=np.empty_like(v)
    f=np.empty((len(me.loop_triangles),3),np.int32)
    me.vertices.foreach_get('co',v.ravel());me.vertices.foreach_get('normal',n.ravel())
    me.loop_triangles.foreach_get('vertices',f.ravel())
    return v,n,f

def dae(path,v,f,normals=None,uv=None):
    # Explicit units/axis and distinct index offsets for Gazebo's COLLADA loader.
    # DART requires one normal per collision vertex, even for collision-only data.
    if normals is None:
        normals=np.zeros_like(v);fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        for k in range(3):np.add.at(normals,f[:,k],fn)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    with path.open('w') as out:
        out.write('<?xml version="1.0"?><COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1"><asset><unit meter="1" name="meter"/><up_axis>Z_UP</up_axis></asset><library_geometries><geometry id="mesh"><mesh>')
        for name,data,params in [('pos',v,'XYZ'),('normal',normals,'XYZ'),('uv',uv,'ST')]:
            if data is None:continue
            out.write(f'<source id="{name}"><float_array id="{name}-array" count="{data.size}">')
            for i in range(0,len(data),16384):np.savetxt(out,data[i:i+16384],fmt='%.7g')
            out.write(f'</float_array><technique_common><accessor source="#{name}-array" count="{len(data)}" stride="{data.shape[1]}">')
            for p in params:out.write(f'<param name="{p}" type="float"/>')
            out.write('</accessor></technique_common></source>')
        out.write('<vertices id="vertices"><input semantic="POSITION" source="#pos"/></vertices>')
        out.write(f'<triangles count="{len(f)}"><input semantic="VERTEX" source="#vertices" offset="0"/><input semantic="NORMAL" source="#normal" offset="1"/>')
        stride=2
        if uv is not None:
            out.write('<input semantic="TEXCOORD" source="#uv" offset="2" set="0"/>');stride=3
        out.write('<p>')
        for i in range(0,len(f),16384):np.savetxt(out,np.repeat(f[i:i+16384],stride,axis=1),fmt='%d')
        out.write('</p></triangles></mesh></geometry></library_geometries><library_visual_scenes><visual_scene id="scene"><node id="node"><instance_geometry url="#mesh"/></node></visual_scene></library_visual_scenes><scene><instance_visual_scene url="#scene"/></scene></COLLADA>')

def bake(obj,source,name,size,folder):
    mat=source.copy();obj.data.materials.clear();obj.data.materials.append(mat)
    n,l=mat.node_tree.nodes,mat.node_tree.links;h=n['HAPKE_CONTROLS']
    scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE'
    
    if h.inputs['Tint'].is_linked:l.new(h.inputs['Tint'].links[0].from_socket,scale.inputs[0])
    else:scale.inputs[0].default_value=h.inputs['Tint'].default_value[:3]
    scale.inputs['Scale'].default_value=.22 if mat.get('lunar_rock') else .19
    diffuse=n.new('ShaderNodeBsdfDiffuse')
    
    if h.inputs['Normal'].is_linked:l.new(h.inputs['Normal'].links[0].from_socket,diffuse.inputs['Normal'])
    l.new(scale.outputs['Vector'],diffuse.inputs['Color'])
    out=next(x for x in n if x.type=='OUTPUT_MATERIAL');l.new(diffuse.outputs[0],out.inputs['Surface'])
    # Remove camera-distance fading for reusable UV texture baking.
    for key,strength in [('METRIC_RELIEF',.5),('METRIC_GRAIN',.22),('METRIC_PITS',.45),('ROCK_FRACTURE_RELIEF',.65)]:
        node=n.get(key)
        if node:
            for link in list(node.inputs['Strength'].links):l.remove(link)
            node.inputs['Strength'].default_value=strength
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1
    s.render.threads_mode='FIXED';s.render.threads=8
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    s.render.bake.use_selected_to_active=False;s.render.bake.margin=12
    for kind in ['albedo','normal']:
        im=bpy.data.images.new(name+'_'+kind,width=size,height=size,alpha=False)
        im.colorspace_settings.name='sRGB' if kind=='albedo' else 'Non-Color'
        tex=n.new('ShaderNodeTexImage');tex.image=im;n.active=tex
        if kind=='albedo':
            em=n.new('ShaderNodeEmission');l.new(scale.outputs['Vector'],em.inputs['Color']);l.new(em.outputs[0],out.inputs['Surface'])
            bpy.ops.object.bake(type='EMIT');l.new(diffuse.outputs[0],out.inputs['Surface']);n.remove(em)
        else:
            s.render.bake.normal_space='TANGENT';bpy.ops.object.bake(type='NORMAL')
        im.filepath_raw=str(folder/(name+'_'+kind+'.png'));im.file_format='PNG';im.save()
        n.remove(tex);bpy.data.images.remove(im)
    obj.data.materials.clear();bpy.data.materials.remove(mat)

def add(p,tag,text=None,**attrs):
    e=E.SubElement(p,tag,attrs)
    if text is not None:e.text=str(text)
    return e

def write(root,path):
    E.indent(root);E.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def mesh_uri(model_id, name):
    return f'model://{model_id}/meshes/{name}.dae'


def visual(link, model_id, name, tex=None, material=None):
    v=add(link,'visual',name=name)
    add(add(add(v,'geometry'),'mesh'),'uri',mesh_uri(model_id,name))
    mat=add(v,'material')
    color=(material or {}).get('color',[1,1,1,1])
    for key in ['ambient','diffuse']:add(mat,key,' '.join(map(str,color)))
    add(mat,'specular','0 0 0 1')
    if material and 'emissive' in material:
        add(mat,'emissive',' '.join(map(str,material['emissive'])))
    pbr=add(add(mat,'pbr'),'metal')
    add(pbr,'metalness',(material or {}).get('metalness',0))
    add(pbr,'roughness',(material or {}).get('roughness',1))
    if tex:
        for kind in ['albedo','normal']:
            add(pbr,kind+'_map',f'model://{model_id}/materials/textures/{tex}_{kind}.png')


def collision(link, model_id, name):
    c=add(link,'collision',name=name)
    add(add(add(c,'geometry'),'mesh'),'uri',mesh_uri(model_id,name))
    ode=add(add(add(c,'surface'),'friction'),'ode')
    add(ode,'mu',.8);add(ode,'mu2',.8)


def decimate_copy(obj, ratio, name):
    co=bpy.data.objects.new(name,obj.data.copy())
    bpy.context.scene.collection.objects.link(co)
    bpy.context.view_layer.objects.active=co
    if ratio<1:
        mod=co.modifiers.new(name,'DECIMATE');mod.ratio=ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return co


def smart_uv(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if not obj.data.uv_layers:obj.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')


def split_mesh(me, faces=None, with_uv=False):
    """Split sharp normals and UV seams into indices understood by Gazebo."""
    v,_,f=arrays(me)
    loops=np.empty_like(f);me.loop_triangles.foreach_get('loops',loops.ravel())
    ns=np.empty((len(me.loops),3),np.float32)
    me.corner_normals.foreach_get('vector',ns.ravel())
    if faces is not None:f=f[faces];loops=loops[faces]
    columns=[f.reshape(-1,1),ns[loops.ravel()]]
    if with_uv:
        uv=np.empty((len(me.loops),2),np.float32)
        me.uv_layers.active.data.foreach_get('uv',uv.ravel())
        columns.append(uv[loops.ravel()])
    unique,inv=np.unique(np.column_stack(columns),axis=0,return_inverse=True)
    return (v[unique[:,0].astype(int)],unique[:,1:4].astype(np.float32),
            inv.reshape(-1,3),unique[:,4:].astype(np.float32) if with_uv else None)


def transform(v,n,matrix):
    m=np.asarray(matrix,dtype=np.float64)
    vv=v@m[:3,:3].T+m[:3,3]
    nn=n@np.linalg.inv(m[:3,:3])
    nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-12)
    return vv.astype(np.float32),nn.astype(np.float32)


def material_values(mat):
    if mat is None:return dict(color=[.19,.19,.19,1],metalness=0,roughness=1)
    nodes=mat.node_tree.nodes if mat.node_tree else []
    bsdf=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    if bsdf:
        result=dict(color=list(bsdf.inputs['Base Color'].default_value),
                    metalness=bsdf.inputs['Metallic'].default_value,
                    roughness=bsdf.inputs['Roughness'].default_value)
        strength=bsdf.inputs['Emission Strength'].default_value
        if strength:
            result['emissive']=[min(1,float(x)*strength) for x in bsdf.inputs['Emission Color'].default_value[:3]]+[1]
        return result
    # The diagnostic must not suggest that stock Ogre2 implements Hapke.
    return dict(color=[.19,.19,.19,1],metalness=0,roughness=1)


def export_extras(objects,link,model_id,meshes,textures,report):
    """Evaluate modifiers, parent transforms, fonts and material slots."""
    groups={};cv=[];cf=[];offset=0;collision_bvhs=[]
    deps=bpy.context.evaluated_depsgraph_get()
    report['extra_objects']=[]
    for index,src in enumerate(objects):
        me=bpy.data.meshes.new_from_object(src.evaluated_get(deps),depsgraph=deps)
        if not me.polygons:
            bpy.data.meshes.remove(me);continue
        name=f'object_{index:04d}'
        obj=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(obj)
        materials=list(me.materials)
        is_rock=any(m and m.get('lunar_rock') for m in materials)
        if is_rock:
            # Full geometry and 2K baked fracture normals for the close-up rocks.
            smart_uv(obj);obj.hide_render=False
            bake(obj,materials[0],name,2048,textures)
            v,n,f,uv=split_mesh(me,with_uv=True);v,n=transform(v,n,src.matrix_world)
            dae(meshes/(name+'.dae'),v,f,n,uv);visual(link,model_id,name,name)
            report['meshes'].append(dict(name=name,source_object=src.name,triangles=len(f)))
        else:
            me.calc_loop_triangles()
            indices=np.empty(len(me.loop_triangles),np.int32)
            me.loop_triangles.foreach_get('material_index',indices)
            for slot in np.unique(indices):
                mat=materials[int(slot)] if int(slot)<len(materials) else None
                key=mat.name if mat else 'Unassigned'
                batch=groups.setdefault(key,dict(v=[],n=[],f=[],offset=0,material=material_values(mat)))
                v,n,f,_=split_mesh(me,indices==slot)
                v,n=transform(v,n,src.matrix_world)
                batch['v'].append(v);batch['n'].append(n);batch['f'].append(f+batch['offset'])
                batch['offset']+=len(v)
        v,n,f=arrays(me);v,n=transform(v,n,src.matrix_world)
        cv.append(v);cf.append(f+offset);offset+=len(v)
        collision_bvhs.append(BVHTree.FromPolygons(v,f,all_triangles=True))
        report['extra_objects'].append(dict(name=src.name,type=src.type,triangles=len(f),rock=is_rock))
        bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(me)
    for i,(key,batch) in enumerate(groups.items()):
        name=f'hardware_{i:02d}'
        f=np.concatenate(batch['f'])
        dae(meshes/(name+'.dae'),np.concatenate(batch['v']),f,np.concatenate(batch['n']))
        visual(link,model_id,name,material=batch['material'])
        report['meshes'].append(dict(name=name,source_material=key,triangles=len(f)))
    if cv:
        dae(meshes/'objects_collision.dae',np.concatenate(cv),np.concatenate(cf))
        collision(link,model_id,'objects_collision')
    report['extra_collision_triangles']=sum(map(len,cf))
    log('Exported extra objects:',len(report['extra_objects']))
    return collision_bvhs


def camera_metadata(s):
    cam=s.camera;q=cam.matrix_world.to_quaternion()
    # Blender camera -Z forward/+Y up -> Gazebo +X forward/+Z up, retaining roll.
    basis=Matrix((q@Vector((0,0,-1)),q@Vector((-1,0,0)),q@Vector((0,1,0)))).transposed()
    pose=list(cam.matrix_world.translation)+list(basis.to_euler('XYZ'))
    width=s.render.resolution_x;height=s.render.resolution_y
    projection=cam.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=width,y=height,
                                      scale_x=s.render.pixel_aspect_x,scale_y=s.render.pixel_aspect_y)
    if cam.data.type=='ORTHO':
        # Stock sensor export uses a perspective view matching the diagnostic plane.
        distance=abs(cam.matrix_world.translation.z)
        hfov=2*math.atan(1/(projection[0][0]*max(distance,.01)))
    else:hfov=2*math.atan(1/projection[0][0])
    factor=min(1,1200/max(width,height))
    return dict(camera_pose_sdf=pose,camera_hfov=hfov,camera_source_type=cam.data.type,
                camera_image_size=[round(width*factor),round(height*factor)],
                camera_projection_note='Perspective matching z=0 plane framing' if cam.data.type=='ORTHO' else 'Perspective; source pose and field of view retained')


def main(source,root,model_id,title):
    start=time.monotonic();modeldir=root/'models'/model_id
    meshes=modeldir/'meshes';textures=modeldir/'materials/textures'
    for p in [meshes,textures,root/'worlds',root/'tests']:p.mkdir(parents=True,exist_ok=True)
    if (modeldir/'model.sdf').exists():raise FileExistsError('Use a new output directory; existing model.sdf found')
    bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
    ground=next((o for o in s.objects if o.type=='MESH' and 'dem_sources' in o),None)
    points=next((o for o in s.objects if o.type=='MESH' and 'instances' in o),None)
    anchor=next((o for o in s.objects if 'generation_report' in o),None)
    sun=next(o for o in s.objects if o.type=='LIGHT' and o.data.type=='SUN')
    extras=[o for o in s.objects if o.type in {'MESH','CURVE','FONT','SURFACE'}
            and o not in (ground,points) and not o.hide_render]
    soil=ground.data.materials[0] if ground else None
    report=dict(source_file=source.name,source_sha256=hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),
        exporter_blender=bpy.app.version_string,model_id=model_id,title=title,
        source_generation=json.loads(anchor['generation_report']) if anchor else None,
        source_settings=json.loads(anchor['settings']) if anchor else None,
        source_hapke={i.name:float(i.default_value) for i in soil.node_tree.nodes['HAPKE_CONTROLS'].inputs if i.type=='VALUE'} if soil else None,
        source_exposure=s.view_settings.exposure,source_sun_energy=sun.data.energy,
        sun_ray_direction=list(-(sun.matrix_world.to_quaternion()@Vector((0,0,1)))),
        coordinate_frame='metres, +X east, +Y north, +Z up; source curvature retained' if ground else 'metres, original Blender diagnostic coordinates',
        material='stock Ogre2 PBR approximation; no Hapke angular BRDF',meshes=[])
    report.update(camera_metadata(s))
    for o in s.objects:o.hide_render=True
    sdf=E.Element('sdf',version='1.10');model=add(sdf,'model',name=model_id)
    add(model,'static','true');link=add(model,'link',name='surface')
    terrain_bvh=None;ground_bounds=None
    if ground:
        v,n,f=arrays(ground.data);v,n=transform(v,n,ground.matrix_world)
        bvh=BVHTree.FromPolygons(v,f,all_triangles=True)
        ground_bounds=[v.min(axis=0).tolist(),v.max(axis=0).tolist()]
        r=np.linalg.norm(v[f].mean(axis=1)[:,:2],axis=1)
        for name,mask in [('terrain_near',r<=128),('terrain_far',r>128)]:
            if not np.any(mask):continue
            used,idx=np.unique(f[mask],return_inverse=True)
            vv,nn,ff=v[used],n[used],idx.reshape(-1,3)
            dae(meshes/(name+'.dae'),vv,ff,nn,vv[:,:2]/64+.5)
            visual(link,model_id,name,'regolith')
            report['meshes'].append(dict(name=name,triangles=len(ff),vertices=len(vv)))
            log('Wrote',name,len(ff))
        co=decimate_copy(ground,.16,'terrain_collision')
        cv,cn,cf=arrays(co.data);cv,cn=transform(cv,cn,ground.matrix_world)
        terrain_bvh=BVHTree.FromPolygons(cv,cf,all_triangles=True)
        radius=report['source_settings']['outer_radius'];halfside=min(150,radius/3)
        errors=[]
        for x,y in np.random.default_rng(170017).uniform(-halfside,halfside,(1500,2)):
            ray=((float(x),float(y),10000),(0,0,-1),20000)
            a=bvh.ray_cast(*ray)[0];b=terrain_bvh.ray_cast(*ray)[0]
            if a is None or b is None:raise RuntimeError('Missing collision surface')
            errors.append(abs(a.z-b.z))
        report['terrain_collision']=dict(triangles=len(cf),coverage_radius_m=radius,
            height_error=dict(samples=1500,sample_square_side_m=2*halfside,
                             mean_m=float(np.mean(errors)),p95_m=float(np.quantile(errors,.95)),max_m=max(errors)))
        dae(meshes/'terrain_collision.dae',cv,cf,cn);collision(link,model_id,'terrain_collision')
        log('Collision',report['terrain_collision']);bpy.data.objects.remove(co,do_unlink=True)
        del v,n,f,r,cv,cn,cf,vv,nn,ff
        bpy.ops.mesh.primitive_plane_add(size=64);plane=bpy.context.object;plane.hide_render=False
        bake(plane,soil,'regolith',4096,textures);bpy.data.objects.remove(plane,do_unlink=True)
    else:report['terrain_collision']=None
    xyz=np.empty((0,3),np.float32);diam=np.empty(0,np.float32)
    report.update(rock_instance_count=0,rock_collision_count=0,rock_collision_triangles=0,rock_collision_min_diameter_m=.15)
    if points:
        xyz=np.empty((len(points.data.vertices),3),np.float32)
        points.data.vertices.foreach_get('co',xyz.ravel())
        diam=np.empty(len(xyz),np.float32);indices=np.empty(len(xyz),np.int32);rot=np.empty_like(xyz)
        for key,values,field in [('diameter',diam,'value'),('prototype',indices,'value'),('rotation',rot,'vector')]:
            points.data.attributes[key].data.foreach_get(field,values.ravel())
        if np.max(np.abs(rot[:,:2]))>1e-6:raise ValueError('Only yaw scatter rotations supported')
        if not np.allclose(np.asarray(points.matrix_world),np.eye(4)):raise ValueError('Scatter transform must be identity')
        coll_v,coll_f,offset=[],[],0;report['rock_instance_count']=len(xyz)
        for i in sorted(np.unique(indices)):
            # Hero rock copies carry the same index; only unlinked prototypes are sources.
            proto=next(o for o in bpy.data.objects if o.get('lunar_prototype_index')==i and o.name not in s.objects)
            rockmat=proto.data.materials[0]
            obj=decimate_copy(proto,.25 if i<12 else 1,'bake_rock');obj.hide_render=False
            smart_uv(obj);texname=f'rock_{i:02d}'
            bake(obj,rockmat,texname,512 if i<12 else 256,textures)
            pv,pn,pf=arrays(obj.data)
            if i<12:
                co=decimate_copy(obj,.125,'rock_collider');lv,_,lf=arrays(co.data)
                bpy.data.objects.remove(co,do_unlink=True)
            else:lv,lf=pv,pf
            pp,nn,ff,uv=split_mesh(obj.data,with_uv=True)
            ids=np.flatnonzero(indices==i);vs,ns,fs,ts=[],[],[],[]
            for j,k in enumerate(ids):
                a=float(rot[k,2]);c,ss=math.cos(a),math.sin(a)
                matrix=np.array([[c,-ss,0],[ss,c,0],[0,0,1]],np.float32)
                vs.append((pp@matrix.T)*diam[k]+xyz[k]);ns.append(nn@matrix.T)
                fs.append(ff+j*len(pp));ts.append(uv)
                if diam[k]>=.15:
                    coll_v.append((lv@matrix.T)*diam[k]+xyz[k]);coll_f.append(lf+offset)
                    offset+=len(lv);report['rock_collision_count']+=1
            name=f'rocks_{i:02d}'
            dae(meshes/(name+'.dae'),np.concatenate(vs),np.concatenate(fs),np.concatenate(ns),np.concatenate(ts))
            visual(link,model_id,name,texname)
            report['meshes'].append(dict(name=name,triangles=len(ids)*len(ff),instances=len(ids)))
            log('Wrote',name,len(ids));bpy.data.objects.remove(obj,do_unlink=True)
        if coll_v:
            dae(meshes/'rocks_collision.dae',np.concatenate(coll_v),np.concatenate(coll_f))
            collision(link,model_id,'rocks_collision')
        report['rock_collision_triangles']=sum(map(len,coll_f))
    extra_bvhs=export_extras(extras,link,model_id,meshes,textures,report)
    # Locate clear, nearly level terrain for the same five falling-box assertions.
    probes=[]
    if ground:
        candidates=[(0,0),(3,0),(0,5),(-6,-3),(12,8)]
        candidates+=list(np.random.default_rng(20261110).uniform(-min(20,radius/4),min(20,radius/4),(4000,2)))
        for x,y in candidates:
            if len(probes)==5:break
            if any(math.hypot(x-a['xy'][0],y-a['xy'][1])<1 for a in probes):continue
            if np.any(np.linalg.norm(xyz[:,:2]-[x,y],axis=1)<diam+.6):continue
            ray=((float(x),float(y),10000),(0,0,-1),20000)
            hit,normal,_,_=terrain_bvh.ray_cast(*ray)
            if hit is None or normal.z<.97:continue
            blocked=False
            for dx,dy in [(0,0),(.3,0),(-.3,0),(0,.3),(0,-.3)]:
                if any(b.ray_cast((float(x+dx),float(y+dy),10000),(0,0,-1),20000)[0] is not None for b in extra_bvhs):
                    blocked=True;break
            if blocked:continue
            probes.append(dict(xy=[float(x),float(y)],visual_z=bvh.ray_cast(*ray)[0].z,collision_z=hit.z))
        far_x=max(abs(ground_bounds[0][0]),abs(ground_bounds[1][0]))+5000
    else:
        # Five points well inside the two flat opposition panels.
        for x,y in [(-2,-2),(-2,0),(-2,2),(2,-1),(2,1)]:
            hits=[b.ray_cast((x,y,10000),(0,0,-1),20000)[0] for b in extra_bvhs]
            z=max(h.z for h in hits if h is not None)
            probes.append(dict(xy=[x,y],visual_z=z,collision_z=z))
        far_x=100
    if len(probes)!=5:raise RuntimeError('Could not find five clear test-probe sites')
    report.update(test_probe_sites=probes,freefall_x_m=far_x,terrain_bounds_m=ground_bounds)
    write(sdf,modeldir/'model.sdf')
    config=E.Element('model');add(config,'name',title);add(config,'version','1.0')
    add(config,'sdf','model.sdf',version='1.10');add(add(config,'author'),'name','Lunar Terrain contributors')
    add(config,'description',f'{source.name}: saved geometry, static collisions and approximate Ogre2 PBR. No Hapke BRDF.')
    write(config,modeldir/'model.config')
    report['export_duration_seconds']=time.monotonic()-start
    (root/'export_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    log('EXPORT COMPLETE',title)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('blend',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--model-id',default='apollo17_terrain');p.add_argument('--title',default='Apollo 17 surface')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    try:main(args.blend.resolve(),args.output.resolve(),args.model_id,args.title)
    except Exception:
        import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(0)
