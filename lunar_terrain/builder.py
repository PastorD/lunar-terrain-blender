"""Staged Blender construction: replace only tagged generated objects."""
import bpy,math,json,uuid
import numpy as np
from mathutils import Vector,Matrix
from .dem import TerrainDEM,status_text
from .surface import Surface,radial_mesh,rock_samples
from . import hapke,solar_disc,rocks
OWNER='_lunar_owner'
def direction(azimuth,elevation):
    a,e=math.radians(azimuth),math.radians(elevation)
    return Vector((math.sin(a)*math.cos(e),math.cos(a)*math.cos(e),math.sin(e)))

def remove_owned(owner,scene):
    for col in list(bpy.data.collections):
        if col.get(OWNER)==owner:
            for obj in list(col.objects):
                if obj.get(OWNER)!=owner and scene.collection not in obj.users_collection:scene.collection.objects.link(obj)
            for child in list(col.children):
                if child.get(OWNER)!=owner and child.name not in scene.collection.children:scene.collection.children.link(child)
    for o in list(bpy.data.objects):
        if o.get(OWNER)==owner:bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections):
        if c.get(OWNER)==owner:bpy.data.collections.remove(c)
    for container in (bpy.data.meshes,bpy.data.curves,bpy.data.cameras,bpy.data.lights,bpy.data.worlds,bpy.data.materials,bpy.data.node_groups):
        for block in list(container):
            if block.get(OWNER)==owner and block.users==0:container.remove(block)

def clear_scene(scene):
    p=scene.lunar_terrain;ids=[c.get(OWNER) for c in scene.collection.children if c.get('_lunar_root')]
    if scene.world and scene.world.get(OWNER) in ids:scene.world=p.previous_world
    if scene.camera and scene.camera.get(OWNER) in ids:scene.camera=p.previous_camera
    for owner in ids:remove_owned(owner,scene)
    p.last_owner='';p.status='Generated terrain cleared'

def apply_lighting(scene,cfg,materials_only=False):
    owner=scene.lunar_terrain.last_owner
    sun=None
    for o in bpy.data.objects:
        if o.get(OWNER)==owner and o.type=='LIGHT' and o.data.type=='SUN':
            sun=o
            if not materials_only:
                o.rotation_euler=direction(cfg.sun_azimuth,cfg.sun_elevation).to_track_quat('Z','Y').to_euler()
                o.data.angle=math.radians(cfg.sun_diameter);o.data.energy=cfg.sun_energy
    for w in bpy.data.worlds:
        if not materials_only and w.get(OWNER)==owner and w.node_tree is not None:
            node=w.node_tree.nodes.get('SOLAR_DISPLAY_RADIANCE')
            if node:node.inputs[1].default_value=1000 if cfg.visible_sun else 0
    replacement_group=None;old_groups=set()
    for mat in bpy.data.materials:
        if mat.get(OWNER)==owner and mat.node_tree is not None:
            n=mat.node_tree.nodes.get('HAPKE_CONTROLS')
            if n:
                if (mat.get('hapke_schema',0)<hapke.SCHEMA or mat.get('surface_schema',0)<hapke.SURFACE_SCHEMA) and sun is not None:
                    group=n.node_tree
                    if mat.get('hapke_schema',0)<hapke.SCHEMA:
                        old_groups.add(group)
                        if replacement_group is None:
                            replacement_group=hapke.build_group(sun);replacement_group[OWNER]=owner
                        group=replacement_group
                    rock=bool(mat.get('lunar_rock','fractures' in mat.name))
                    hapke.material(group,mat.name,rock,existing=mat)
                hapke.set_controls(mat,cfg)
    for group in old_groups:
        if group and group.users==0 and group.get(OWNER)==owner:bpy.data.node_groups.remove(group)
    for o in scene.objects:
        if o.get(OWNER)==owner and 'generation_report' in o:
            o['appearance_settings']=json.dumps({k:getattr(cfg,k) for k in ('appearance','single_scattering_albedo','phase_b','phase_c','photometric_roughness','shoe_amplitude','shoe_width','cboe_amplitude','cboe_width','soil_tint','exposure','regolith_relief')},indent=2)
    bpy.context.view_layer.update()
    scene.view_settings.exposure=cfg.exposure

def upgrade_rocks(scene,cfg):
    """Update only owned, instanced prototypes using their original scene seed."""
    owner=scene.lunar_terrain.last_owner
    if not owner:raise ValueError('Build terrain or open an existing Lunar Terrain scene first')
    seed=scene.lunar_terrain.seed
    for o in scene.objects:
        if o.get(OWNER)==owner and 'generation_report' in o:
            seed=int(json.loads(o['generation_report']).get('seed',seed));break
    count=0
    for col in bpy.data.collections:
        if col.get(OWNER)!=owner or 'rock prototypes' not in col.name:continue
        for obj in col.objects:
            if obj.get(OWNER)!=owner or obj.type!='MESH':continue
            index=obj.get('lunar_prototype_index')
            if index is None:
                try:index=int(obj.name.split(' | ',1)[0].split()[-1])
                except ValueError:continue
            if not 0<=index<24:continue
            if obj.data.get('lunar_rock_schema',0)<rocks.SCHEMA:
                rocks.populate_mesh(obj.data,seed,index);count+=1
            obj['lunar_prototype_index']=index
    cfg.exposure=scene.view_settings.exposure
    apply_lighting(scene,cfg,materials_only=True)
    return count


class Build:
    def __init__(self,scene,cfg,cache_dir):
        self.scene,self.cfg,self.cache_dir=scene,cfg,cache_dir;self.owner=uuid.uuid4().hex;self.committed=False;self.root=None;self.surface=None;self.stats={}
    def tag(self,data):data[OWNER]=self.owner;return data
    def collection(self,name,parent=None):
        c=self.tag(bpy.data.collections.new(name))
        if parent is not None:parent.children.link(c)
        return c
    def object(self,name,data,col):
        o=self.tag(bpy.data.objects.new(name,data));col.objects.link(o)
        if data is not None:self.tag(data)
        return o
    def camera(self,name,loc,heading,pitch,lens,col):
        o=self.object(name,bpy.data.cameras.new(name),col);o.location=loc
        o.rotation_euler=direction(heading,pitch).to_track_quat('-Z','Y').to_euler()
        o.data.lens=lens;o.data.sensor_width=36;o.data.clip_start=.03;o.data.clip_end=150000;return o
    def abort(self):
        if not self.committed:remove_owned(self.owner,self.scene)
    def prototypes(self,material):
        col=self.collection('Lunar • rock prototypes (instanced)')
        for i in range(24):
            me=self.tag(bpy.data.meshes.new(f'Fractured rock {i:02d}'))
            rocks.populate_mesh(me,self.cfg.seed,i)
            o=self.object(f'Rock {i:02d} | '+('detailed' if i<12 else 'light'),me,col);me.materials.append(material)
            o['lunar_prototype_index']=i
            o['normalization']='Unit equivalent projected diameter; instance scale is diameter in metres'
        return col
    def scatter(self,xyz,diameter,rotation,indices,prototypes,col):
        me=self.tag(bpy.data.meshes.new('Rock distribution points'));me.vertices.add(len(xyz));me.vertices.foreach_set('co',xyz.ravel())
        for name,kind,values,field in [('diameter','FLOAT',diameter,'value'),('rotation','FLOAT_VECTOR',rotation,'vector'),('prototype','INT',indices,'value')]:
            a=me.attributes.new(name,kind,'POINT');a.data.foreach_set(field,values.ravel())
        o=self.object('Lunar • angular rocks and fine fragments',me,col);ng=self.tag(bpy.data.node_groups.new('Lunar rock instancing','GeometryNodeTree'))
        for io in ('INPUT','OUTPUT'):ng.interface.new_socket(name='Geometry',in_out=io,socket_type='NodeSocketGeometry')
        n,l=ng.nodes,ng.links;inp=n.new('NodeGroupInput');out=n.new('NodeGroupOutput');inp.location=(-600,150);out.location=(400,150)
        ci=n.new('GeometryNodeCollectionInfo');ci.location=(-600,-40);ci.inputs['Collection'].default_value=prototypes;ci.inputs['Separate Children'].default_value=True;ci.inputs['Reset Children'].default_value=True
        inst=n.new('GeometryNodeInstanceOnPoints');inst.location=(100,150);inst.inputs['Pick Instance'].default_value=True
        l.new(inp.outputs['Geometry'],inst.inputs['Points']);l.new(ci.outputs['Instances'],inst.inputs['Instance'])
        for i,(name,typ,socket) in enumerate([('diameter','FLOAT','Scale'),('rotation','FLOAT_VECTOR','Rotation'),('prototype','INT','Instance Index')]):
            a=n.new('GeometryNodeInputNamedAttribute');a.data_type=typ;a.inputs['Name'].default_value=name;a.location=(-280,-100-i*150);l.new(a.outputs['Attribute'],inst.inputs[socket])
        l.new(inst.outputs['Instances'],out.inputs['Geometry']);o.modifiers.new('Instances (editable point attributes)','NODES').node_group=ng;o['instances']=len(xyz);return o
    def steps(self):
        try:
            cfg,scene=self.cfg,self.scene;self.root=self.collection('Lunar Terrain • generating',scene.collection);self.root['_lunar_root']=True
            yield 'Reading real lunar DEMs'
            dem=TerrainDEM(cfg.latitude,cfg.longitude,self.cache_dir,cfg.custom_dem);self.surface=surface=Surface(dem,cfg)
            self.stats['dem_sources_at_origin']=dem.description();self.stats['warnings']=dem.warnings;self.stats['dem_resolution']=dem.resolution_report(cfg.outer_radius,cfg.focus_x,cfg.focus_y)
            yield from surface.prepare();g=radial_mesh(surface,cfg)
            while True:
                try:yield next(g)
                except StopIteration as e:vertices,faces,lod=e.value;break
            me=self.tag(bpy.data.meshes.new('Joined multiresolution lunar surface'));me.vertices.add(len(vertices));me.vertices.foreach_set('co',vertices.ravel())
            me.loops.add(faces.size);me.loops.foreach_set('vertex_index',faces.ravel());me.polygons.add(len(faces))
            me.polygons.foreach_set('loop_start',np.arange(len(faces),dtype=np.int32)*3);me.polygons.foreach_set('loop_total',np.full(len(faces),3,np.int32));me.polygons.foreach_set('use_smooth',np.ones(len(faces),bool))
            a=me.attributes.new('lod_band','INT','POINT');a.data.foreach_set('value',lod);me.update()
            ground=self.object('Lunar • real DEM + synthetic regolith',me,self.collection('01 • Continuous terrain',self.root))
            self.stats.update(vertices=len(vertices),triangles=len(faces),craters=surface.crater_count,artist_micro_craters=surface.micro_crater_count,latitude=cfg.latitude,longitude_east=cfg.longitude%360,origin_elevation_m=dem.h0,near_spacing_m=cfg.mesh_spacing,outer_radius_m=cfg.outer_radius,seed=cfg.seed,detail_focus_xy_m=[cfg.focus_x,cfg.focus_y])
            del vertices,faces,lod
            yield 'Building Sun-linked Hapke regolith'
            lights=self.collection('03 • Sun and cameras',self.root);sun=self.object('Lunar Sun',bpy.data.lights.new('Lunar Sun','SUN'),lights)
            sun.rotation_euler=direction(cfg.sun_azimuth,cfg.sun_elevation).to_track_quat('Z','Y').to_euler();sun.data.energy=cfg.sun_energy;sun.data.angle=math.radians(cfg.sun_diameter)
            group=self.tag(hapke.build_group(sun));soil=self.tag(hapke.material(group,'Lunar • granular regolith'));rock=self.tag(hapke.material(group,'Lunar • dust-coated fractures',True))
            for mat in (soil,rock):
                hapke.set_controls(mat,cfg)
            me.materials.append(soil);ground['coordinate_frame']='Metres; +X east, +Y north, +Z up at the selected location'
            ground['sub_DEM_detail']='Synthetic: CE-6 analogue sizes, user-controlled abundance, artist-authored fine detail'
            yield 'Constructing angular rock prototypes'
            prototypes=self.prototypes(rock);xyz,diam,rot,index,stats=rock_samples(surface,cfg)
            self.scatter(xyz,diam,rot,index,prototypes,self.collection('02 • Rock field',self.root));self.stats.update(rocks=len(xyz),rock_coverage_k=cfg.rock_coverage,rock_zones=stats)
            del xyz,diam,rot,index
            yield 'Placing camera and optional outpost'
            camera=self.camera('Lunar • surface camera',(0,0,float(surface.height(0,0))+cfg.camera_height),cfg.camera_heading,cfg.camera_pitch,cfg.camera_lens,lights)
            if cfg.focus_camera_matrix:camera.matrix_world=Matrix(cfg.focus_camera_matrix);camera.data.lens=cfg.focus_camera_lens
            self.camera('Lunar • look at Sun',(0,0,float(surface.height(0,0))+cfg.camera_height),cfg.sun_azimuth,cfg.sun_elevation,100,lights)
            if cfg.include_outpost:
                from . import outpost
                col=self.collection('04 • Concept rover and moon base',self.root);containers=[bpy.data.objects,bpy.data.meshes,bpy.data.curves,bpy.data.materials];before=[set(c) for c in containers]
                try:outpost.materials();outpost.rover(col,surface);outpost.base(col,surface);outpost.astronaut(col,surface,0,16)
                finally:
                    for container,old in zip(containers,before):
                        for block in set(container)-old:self.tag(block)
                oc=self.camera('Lunar • outpost camera',(13,-43,float(surface.height(13,-43))+3.2),350,.5,36,lights)
                if cfg.focus_mode=='AUTO':camera=oc
            world=self.tag(bpy.data.worlds.new('Lunar • vacuum and visible solar disc'));solar_disc.add(world,sun)
            world.node_tree.nodes['SOLAR_DISPLAY_RADIANCE'].inputs[1].default_value=1000 if cfg.visible_sun else 0
            anchor=self.object('Lunar location • metadata',None,self.root);anchor.empty_display_type='PLAIN_AXES';anchor.empty_display_size=2
            anchor['generation_report']=json.dumps(self.stats,indent=2);anchor['settings']=json.dumps(vars(cfg),indent=2);ground['dem_sources']=json.dumps(self.stats['dem_sources_at_origin'])
            yield 'Committing completed terrain'
            previous=[c.get(OWNER) for c in scene.collection.children if c!=self.root and c.get('_lunar_root')]
            if not previous:scene.lunar_terrain.previous_camera=scene.camera;scene.lunar_terrain.previous_world=scene.world
            if cfg.setup_scene:
                scene.camera=camera;scene.world=world;scene.render.engine='CYCLES';scene.cycles.samples=cfg.samples;scene.cycles.use_denoising=True
                scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=cfg.exposure
                scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
            else:
                if scene.camera and scene.camera.get(OWNER) in previous:scene.camera=camera
                if scene.world and scene.world.get(OWNER) in previous:scene.world=world
            p=scene.lunar_terrain;p.last_owner=self.owner;self.root.name=f'Lunar Terrain • {cfg.latitude:.4f}, {cfg.longitude%360:.4f} E';p.stats=json.dumps(self.stats)
            p.dem_status=status_text(self.stats['dem_resolution']);p.dem_report=json.dumps(self.stats['dem_resolution'])
            for old in previous:remove_owned(old,scene)
            self.committed=True;p.status=f"Ready: {self.stats['triangles']:,} triangles, {self.stats['rocks']:,} rocks"
            for screen in bpy.data.screens:
                for area in screen.areas:
                    if area.type=='VIEW_3D':
                        area.spaces.active.clip_end=150000;area.spaces.active.show_region_ui=True
                        if cfg.setup_scene:area.spaces.active.region_3d.view_perspective='CAMERA'
            yield p.status
        finally:
            if not self.committed:self.abort()
