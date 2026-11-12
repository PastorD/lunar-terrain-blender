"""Lunar Terrain: real DEMs, spatial LOD, surface analogues and Hapke lighting."""
# Extension metadata lives in blender_manifest.toml.
import bpy,traceback,json
from pathlib import Path
from types import SimpleNamespace
from bpy.props import FloatProperty,IntProperty,BoolProperty,StringProperty,EnumProperty,PointerProperty,FloatVectorProperty
from bpy_extras.io_utils import ImportHelper
from . import dem,builder,appearance,catalog,sites
_active_job=None
FIELDS=('appearance regolith_relief phase_b phase_c photometric_roughness shoe_amplitude shoe_width cboe_amplitude cboe_width soil_tint albedo_variation rock_albedo_ratio latitude longitude custom_dem outer_radius detail_radius mesh_spacing focus_mode curvature seed rock_coverage min_rock micro_density max_rocks crater_density micro_craters crater_depth roughness sun_azimuth sun_elevation sun_diameter sun_energy visible_sun opposition single_scattering_albedo exposure camera_height camera_heading camera_pitch camera_lens include_outpost setup_scene samples native_radius dem_budget_mb').split()
def cache_path():
    if __package__.startswith('bl_ext.'):return bpy.utils.extension_path_user(__package__,path='dem_cache',create=True)
    return bpy.utils.user_resource('DATAFILES',path='lunar_terrain/dem_cache',create=True)
def snapshot(p):
    v={k:getattr(p,k) for k in FIELDS};v['soil_tint']=list(p.soil_tint);v['rock_coverage']/=100;v['custom_dem']=bpy.path.abspath(p.custom_dem) if p.custom_dem else ''
    if p.outer_radius<1.8*p.detail_radius:raise ValueError('Terrain radius must be at least 1.8 times near detail radius')
    v['focus_x'],v['focus_y']=(13.,-43.) if p.include_outpost and p.focus_mode=='AUTO' else (0.,0.)
    v['focus_camera_matrix']=[];v['focus_camera_lens']=p.camera_lens
    if p.focus_mode=='CAMERA':
        c=p.id_data.camera
        if c is None or c.data.type!='PERSP':raise ValueError('Active-camera focus needs an active perspective camera')
        v['focus_x'],v['focus_y']=float(c.matrix_world.translation.x),float(c.matrix_world.translation.y)
        if max(abs(v['focus_x']),abs(v['focus_y']))>50000:raise ValueError('Active camera must be within 50 km of the location origin')
        v['focus_camera_matrix']=[list(row) for row in c.matrix_world];v['focus_camera_lens']=c.data.lens
    return SimpleNamespace(**v)

def location_changed(self,context):
    self.dem_status='Location changed; inspect cache or rebuild'
    self.dem_report='{}';self.dem_download_report='{}';self.download_status=''

class LUNAR_PG_settings(bpy.types.PropertyGroup):
    site: EnumProperty(name='Location preset',items=[('APOLLO17','Apollo 17 / Taurus–Littrow','LROC NAC 2 m native grid available; Apollo-style surface'),('SOUTH','South pole / Connecting Ridge','LROC NAC 2 m where valid, adjusted LOLA 5 m and coarser context'),('CE6',"Chang’e-6 / Apollo basin",'LROC NAC 4 m native grid available and published analogue abundance'),('BLUEGHOST','Blue Ghost 1 / Mare Crisium','LROC NAC 3 m grid; cool reference appearance, low Sun and a view toward the shadow direction'),('CH3','Chandrayaan-3 / Shiv Shakti','LROC NAC 3 m grid; neutral Pragyan NavCam appearance, sparse fragments and rover-height framing')]+[(key,v['name'],v['role']) for key,v in sites.POLAR_SITES.items()],default='APOLLO17')
    latitude: FloatProperty(name='Latitude',description='Planetocentric degrees; north positive',default=20.1908,min=-90,max=90,precision=5,update=location_changed)
    longitude: FloatProperty(name='Longitude E',description='East-positive degrees; negative west longitudes accepted',default=30.7717,min=-360,max=360,precision=5,update=location_changed)
    custom_dem: StringProperty(name='Extra DEM pack',description='Optional georeferenced .npz from the supplied converter',subtype='FILE_PATH')
    download_first: BoolProperty(name='Download finer DEM before building',default=True,description='Finest supported native grid near the detail focus; respects Blender Allow Online Access and download budget')
    native_radius: FloatProperty(name='Native DEM radius',description='Finest supported DEM grid within this radius of the detail focus; distant terrain retains coarser context',default=2000,min=100,max=50000,subtype='DISTANCE',unit='LENGTH')
    dem_budget_mb: IntProperty(name='Download budget (MiB)',description='Maximum elevation transfer per operation; a JAXA tile may require 32 MiB',default=1024,min=16,max=32768)
    dem_report: StringProperty(default='{}')
    dem_download_report: StringProperty(default='{}')
    download_status: StringProperty(default='')
    outer_radius: FloatProperty(name='Terrain radius',default=20000,min=100,max=50000,subtype='DISTANCE',unit='LENGTH')
    detail_radius: FloatProperty(name='Near detail radius',default=30,min=10,max=150,subtype='DISTANCE',unit='LENGTH')
    mesh_spacing: FloatProperty(name='Near mesh spacing',description='Geometry posting, not measured DEM resolution',default=.10,min=.06,max=2,subtype='DISTANCE',unit='LENGTH',precision=3)
    focus_mode: EnumProperty(name='Near detail focus',items=[('AUTO','Automatic','Surface camera or optional outpost camera'),('LOCATION','Location origin','Fine terrain at local X=0, Y=0'),('CAMERA','Active camera','Retain the active camera view and build fine terrain below it')],default='AUTO')
    curvature: BoolProperty(name='Lunar curvature',default=True)
    seed: IntProperty(name='Random seed',default=170017,min=0,max=2147480000)
    rock_coverage: FloatProperty(name='Rock area k (%)',description='Projected-area abundance in the exponential analogue model; Apollo value is artistic',default=1,min=0,max=5,precision=3)
    min_rock: FloatProperty(name='Smallest rock',default=.025,min=.01,max=.19,subtype='DISTANCE',unit='LENGTH',precision=3)
    micro_density: FloatProperty(name='Fine fragments / m²',description='Artist-authored 5–25 mm fragments within 20 m; separate from measured analogue',default=20,min=0,max=150)
    max_rocks: IntProperty(name='Instance cap',default=200000,min=1000,max=1000000)
    crater_density: FloatProperty(name='Crater abundance',description='Multiplier on the measured CE-6 interior-window counts',default=.5,min=0,max=2)
    micro_craters: FloatProperty(name='Small craterlets / m²',description='Artistic 0.20–0.52 m pits, below catalogue completeness; 0 disables',default=.8,min=0,max=2)
    crater_depth: FloatProperty(name='Crater depth scale',description='Multiplier on analogue depth/diameter; lower means more degraded',default=.65,min=.1,max=1.5)
    roughness: FloatProperty(name='Fine ground relief',default=1,min=0,max=3)
    sun_azimuth: FloatProperty(name='Sun azimuth',description='Clockwise from north toward east, degrees',default=300,min=0,max=360)
    sun_elevation: FloatProperty(name='Sun elevation',description='Art-directed angle, not a date-based ephemeris; use grazing angles at poles',default=18,min=-10,max=90)
    sun_diameter: FloatProperty(name='Sun diameter (°)',default=.53,min=.05,max=2,precision=3)
    sun_energy: FloatProperty(name='Sun strength',default=3.8,min=0,max=30)
    visible_sun: BoolProperty(name='Camera-visible Sun',default=True)
    opposition: FloatProperty(name='Opposition effect',description='Strength of Hapke shadow-hiding and coherent-backscatter surges',default=1,min=0,max=1)
    single_scattering_albedo: FloatProperty(name='Single-scattering albedo',default=.19069648,min=.001,max=.99,precision=4)
    exposure: FloatProperty(name='Exposure (stops)',default=4.4,min=-6,max=6)
    appearance: EnumProperty(name='Reference appearance',items=[('APOLLO','Apollo references','Neutral and brighter; Apollo 17 regional prior'),('CHANGE','Chang’e references','Warm and darker; Chang’e-6 regional prior'),('BLUEGHOST','Blue Ghost references','Cool, bright regolith and deep shadows; Mare Crisium regional prior with artistic colour balance'),('CH3','Chandrayaan-3 / Pragyan NavCam','Neutral grayscale surface references and local regional Hapke prior')],default='APOLLO')
    phase_b: FloatProperty(name='2HG width b',default=.26402950,min=0,max=.95,precision=4)
    phase_c: FloatProperty(name='2HG backward balance c',description='c in [-1,1]; backward lobe weight is (1+c)/2',default=.07014839,min=-1,max=1,precision=4)
    photometric_roughness: FloatProperty(name='Photometric roughness (°)',description='Unresolved facet slopes in the Hapke correction',default=23.656601,min=0,max=45,precision=3)
    shoe_amplitude: FloatProperty(name='SHOE amplitude',default=2.18679166,min=0,max=5,precision=4)
    shoe_width: FloatProperty(name='SHOE width h',description='Dimensionless tangent half-angle width; not degrees',default=.07088306,min=.0001,max=1,precision=5)
    cboe_amplitude: FloatProperty(name='CBOE amplitude',description='Keep zero with LROC priors; SHOE already includes the unresolved surge',default=0,min=0,max=2,precision=4)
    cboe_width: FloatProperty(name='CBOE width h',default=1,min=.0001,max=1,precision=5)
    soil_tint: FloatVectorProperty(name='Soil color balance',description='Broadband appearance color, independent of 566 nm photometry',subtype='COLOR',size=3,default=(.95,.95,.95),min=0,max=1)
    albedo_variation: FloatProperty(name='Soil color variation',default=.10,min=0,max=.5,precision=3)
    regolith_relief: FloatProperty(name='Soil texture relief',description='Gain on centimetre and millimetre soil bump detail; independent of measured DEM and rock geometry',default=1,min=0,max=4,precision=2)
    rock_albedo_ratio: FloatProperty(name='Rock / soil albedo',default=1.08,min=.5,max=2,precision=2)
    camera_height: FloatProperty(name='Eye height',default=1.65,min=.2,max=100,subtype='DISTANCE',unit='LENGTH')
    camera_heading: FloatProperty(name='Camera heading',default=60,min=0,max=360)
    camera_pitch: FloatProperty(name='Camera pitch',description='Positive up, negative down, degrees',default=-8,min=-89,max=89)
    camera_lens: FloatProperty(name='Lens (mm)',default=40,min=12,max=200)
    include_outpost: BoolProperty(name='Add concept rover and moon base',default=False)
    setup_scene: BoolProperty(name='Set camera, world and Cycles',default=True)
    samples: IntProperty(name='Render samples',default=64,min=8,max=4096)
    busy: BoolProperty(default=False,options={'SKIP_SAVE'})
    status: StringProperty(default='Choose a location and build terrain')
    dem_status: StringProperty(default='Inspect DEM to see the loaded grid at this location')
    stats: StringProperty(default='{}')
    last_owner: StringProperty(default='')
    previous_world: PointerProperty(type=bpy.types.World)
    previous_camera: PointerProperty(type=bpy.types.Object)

class LUNAR_OT_preset(bpy.types.Operator):
    bl_idname='lunar.apply_preset';bl_label='Apply location and look';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return _active_job is None
    def execute(self,context):
        p=context.scene.lunar_terrain
        # Reset framing on location changes so a wide Blue Ghost view does not
        # carry into an Apollo or Chang'e location preset.
        p.camera_height,p.camera_lens=1.65,40
        p.roughness=1.
        if p.site=='APOLLO17':
            p.latitude,p.longitude=20.1908,30.7717;p.rock_coverage,p.crater_density,p.crater_depth=1,.5,.65;p.micro_density,p.micro_craters=20,.8
            p.sun_elevation,p.sun_azimuth,p.exposure=18,300,1.9;p.camera_heading,p.camera_pitch=60,-8
        elif p.site=='SOUTH':
            p.latitude,p.longitude=-89.438788,222.844980;p.rock_coverage,p.crater_density,p.crater_depth=.179,.65,.8;p.micro_density,p.micro_craters=8,.35
            p.sun_elevation,p.sun_azimuth,p.exposure=1.7,110,1.3;p.camera_heading,p.camera_pitch=350,-5
        elif p.site=='BLUEGHOST':
            p.latitude,p.longitude=18.5623,61.8103
            p.rock_coverage,p.crater_density,p.crater_depth=.12,.65,.85
            p.micro_density,p.micro_craters=10,.5
            p.sun_elevation,p.sun_azimuth=2.5,90
            p.sun_energy,p.sun_diameter,p.visible_sun=3.8,.53,True
            p.roughness=1.
            p.camera_heading,p.camera_pitch=270,1
            p.camera_height,p.camera_lens=2.,20
        elif p.site=='CH3':
            p.latitude,p.longitude=-69.373,32.319
            # Visual analogue choices, not a recovered NavCam population fit.
            p.rock_coverage,p.crater_density,p.crater_depth=.07,.35,.60
            p.micro_density,p.micro_craters=12,.65
            p.roughness=2.0
            p.sun_elevation,p.sun_azimuth=18,355
            p.sun_energy,p.sun_diameter,p.visible_sun=3.8,.53,True
            p.camera_heading,p.camera_pitch=90,-6
            p.camera_height,p.camera_lens=.65,51
        elif p.site in sites.POLAR_SITES:
            sites.apply(p,p.site)
        else:
            p.latitude,p.longitude=-41.6385,206.0148;p.rock_coverage,p.crater_density,p.crater_depth=.179,1,1;p.micro_density,p.micro_craters=0,0
            p.sun_elevation,p.sun_azimuth,p.exposure=15,300,1.3;p.camera_heading,p.camera_pitch=60,-8
        appearance.apply(p,'APOLLO' if p.site in sites.POLAR_SITES else {'APOLLO17':'APOLLO','BLUEGHOST':'BLUEGHOST','CH3':'CH3'}.get(p.site,'CHANGE'))
        p.status=sites.POLAR_SITES[p.site]['role'] if p.site in sites.POLAR_SITES else 'Preset applied; build terrain to use it';return {'FINISHED'}

class LUNAR_OT_appearance(bpy.types.Operator):
    bl_idname='lunar.apply_appearance';bl_label='Apply Reference Appearance';bl_options={'REGISTER','UNDO'}
    bl_description='Update existing Hapke materials and exposure without rebuilding terrain or moving the Sun'
    @classmethod
    def poll(cls,c):return _active_job is None
    def execute(self,c):
        p=c.scene.lunar_terrain;appearance.apply(p,p.appearance)
        if p.last_owner:builder.apply_lighting(c.scene,snapshot(p),materials_only=True)
        p.status='Reference appearance applied; exposure remains editable';return {'FINISHED'}
class LUNAR_OT_photometry(bpy.types.Operator):
    bl_idname='lunar.load_photometry';bl_label='Use LROC Parameters at Location';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,c):return _active_job is None
    def execute(self,c):
        p=c.scene.lunar_terrain
        p.exposure=c.scene.view_settings.exposure
        try:appearance.set_photometry(p,p.latitude,p.longitude)
        except ValueError as e:self.report({'WARNING'},str(e));return {'CANCELLED'}
        if p.last_owner:builder.apply_lighting(c.scene,snapshot(p),materials_only=True)
        p.status='LROC regional prior applied';return {'FINISHED'}

class LUNAR_OT_build(bpy.types.Operator):
    bl_idname='lunar.build';bl_label='Build / Rebuild Lunar Terrain';bl_options={'REGISTER','UNDO'}
    bl_description='Create terrain from real DEMs and replace only previous generated objects'
    download_only: BoolProperty(default=False,options={'HIDDEN'})
    @classmethod
    def poll(cls,context):return context.scene is not None and _active_job is None
    def _steps(self):
        p=self._scene.lunar_terrain;cfg=snapshot(p)
        if p.download_first or self.download_only:
            if not bpy.app.online_access:
                if self.download_only:raise RuntimeError('Enable Allow Online Access in Preferences > System to download DEMs')
                p.download_status='Offline: using bundled and cached native cells'
            else:
                lat,lon=cfg.latitude,cfg.longitude
                if cfg.focus_x or cfg.focus_y:
                    local=dem.TerrainDEM(lat,lon,cache_path(),cfg.custom_dem);a,b=local.geodetic([cfg.focus_x],[cfg.focus_y]);lat,lon=float(a[0]),float(b[0])
                report={}
                for _,message in dem.download_region(lat,lon,cfg.outer_radius,cache_path(),native_radius_m=cfg.native_radius,budget_mb=cfg.dem_budget_mb,report=report):yield message
                p.dem_download_report=json.dumps(report);p.dem_report=json.dumps(report['loaded'])
                p.dem_status=dem.status_text(report['loaded'],'Cached')
                p.download_status=('Complete' if report['complete'] else 'Partial: see DEM report')+f'; native radius {min(cfg.native_radius,cfg.outer_radius)/1000:g} km'
        if self.download_only:p.status=p.download_status+'; rebuild terrain to use cached data';yield p.status
        else:self._build=builder.Build(self._scene,cfg,cache_path());yield from self._build.steps()
    def _start(self,context):
        global _active_job
        self._scene=context.scene;self._build=None;self._timer=None;self._gen=self._steps();_active_job=self;self._scene.lunar_terrain.busy=True
    def _finish(self,context,cancelled=False):
        global _active_job
        self._gen.close()
        if self._build and not self._build.committed:self._build.abort()
        if self._timer:context.window_manager.event_timer_remove(self._timer);self._timer=None
        self._scene.lunar_terrain.busy=False
        if cancelled:self._scene.lunar_terrain.status='Cancelled; previous terrain retained'
        _active_job=None
    def execute(self,context):
        self._start(context)
        try:
            for message in self._gen:
                self._scene.lunar_terrain.status=message
                if bpy.app.background:print('LUNAR:',message,flush=True)
            self.report({'INFO'},self._scene.lunar_terrain.status);return {'FINISHED'}
        except Exception as e:
            traceback.print_exc();self._scene.lunar_terrain.status=str(e);self.report({'ERROR'},str(e));return {'CANCELLED'}
        finally:self._finish(context)
    def invoke(self,context,event):
        self._start(context);self._timer=context.window_manager.event_timer_add(.03,window=context.window);context.window_manager.modal_handler_add(self);return {'RUNNING_MODAL'}
    def modal(self,context,event):
        if event.type=='ESC':
            committed=bool(self._build and self._build.committed);self._finish(context,not committed);return {'FINISHED'} if committed else {'CANCELLED'}
        if event.type=='TIMER' and event.timer==self._timer:
            try:
                self._scene.lunar_terrain.status=next(self._gen)
                if context.area:context.area.tag_redraw()
            except StopIteration:self._finish(context);return {'FINISHED'}
            except Exception as e:
                traceback.print_exc();self._scene.lunar_terrain.status=str(e);self._finish(context);self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def cancel(self,context):self._finish(context,True)

class LUNAR_OT_light(bpy.types.Operator):
    bl_idname='lunar.update_light';bl_label='Update Lighting and Materials';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,c):return _active_job is None and bool(c.scene.lunar_terrain.last_owner)
    def execute(self,c):builder.apply_lighting(c.scene,snapshot(c.scene.lunar_terrain));return {'FINISHED'}
class LUNAR_OT_clear(bpy.types.Operator):
    bl_idname='lunar.clear';bl_label='Clear Generated Terrain';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,c):return _active_job is None and bool(c.scene.lunar_terrain.last_owner)
    def execute(self,c):builder.clear_scene(c.scene);return {'FINISHED'}

class LUNAR_OT_rocks(bpy.types.Operator):
    bl_idname='lunar.update_rocks';bl_label='Upgrade Rock Detail';bl_options={'REGISTER','UNDO'}
    bl_description='Add detailed rock surfaces to an existing scene while retaining terrain, rock placements and camera'
    @classmethod
    def poll(cls,c):return _active_job is None and bool(c.scene.lunar_terrain.last_owner)
    def execute(self,c):
        count=builder.upgrade_rocks(c.scene,snapshot(c.scene.lunar_terrain))
        self.report({'INFO'},f'Rock surfaces updated; {count} prototypes upgraded');return {'FINISHED'}

class LUNAR_OT_inspect_dem(bpy.types.Operator):
    bl_idname='lunar.inspect_dem';bl_label='Inspect Cached DEM Resolution'
    @classmethod
    def poll(cls,c):return _active_job is None
    def execute(self,c):
        p=c.scene.lunar_terrain;cfg=snapshot(p)
        report=dem.TerrainDEM(p.latitude,p.longitude,cache_path(),cfg.custom_dem).resolution_report(p.outer_radius,cfg.focus_x,cfg.focus_y)
        p.dem_report=json.dumps(report);p.dem_status=dem.status_text(report,'Cached')
        return {'FINISHED'}

class LUNAR_OT_dem_map(bpy.types.Operator):
    bl_idname='lunar.dem_map';bl_label='Open DEM Coverage Map'
    def execute(self,c):
        bpy.ops.wm.url_open(url=Path(__file__).with_name('data').joinpath('Lunar_DEM_Map.html').as_uri());return {'FINISHED'}

class LUNAR_OT_photo_references(bpy.types.Operator):
    bl_idname='lunar.photo_references';bl_label='Chandrayaan-3 photo references'
    bl_description='Open the reviewed photo catalogue; original images need internet access'
    def execute(self,c):
        bpy.ops.wm.url_open(url=Path(__file__).with_name('data').joinpath('Chandrayaan3_References.html').as_uri());return {'FINISHED'}

class LUNAR_OT_atlas(bpy.types.Operator):
    bl_idname='lunar.atlas';bl_label='Open Lunar Atlas'
    bl_description='Interactive location map, photographs and renders; images need internet'
    def execute(self,c):
        bpy.ops.wm.url_open(url=Path(__file__).with_name('data').joinpath('Lunar_Atlas.html').as_uri());return {'FINISHED'}

class LUNAR_OT_import_location(bpy.types.Operator,ImportHelper):
    bl_idname='lunar.import_location';bl_label='Import Atlas Location';bl_options={'REGISTER','UNDO'}
    filename_ext='.json'
    filter_glob:StringProperty(default='*.json',options={'HIDDEN'})
    @classmethod
    def poll(cls,c):return _active_job is None
    def execute(self,c):
        try:
            path=Path(self.filepath)
            if path.stat().st_size>16384:raise ValueError('Location JSON is too large')
            known={v.identifier for v in c.scene.lunar_terrain.bl_rna.properties['site'].enum_items}
            key=sites.location_from_json(json.loads(path.read_text()),known)
        except (OSError,ValueError,TypeError) as error:
            self.report({'ERROR'},str(error));return {'CANCELLED'}
        c.scene.lunar_terrain.site=key
        return bpy.ops.lunar.apply_preset()

class LUNAR_OT_dem_report(bpy.types.Operator):
    bl_idname='lunar.dem_report';bl_label='Show DEM Source Report'
    def execute(self,c):
        p=c.scene.lunar_terrain;t=bpy.data.texts.get('Lunar_DEM_Report.json') or bpy.data.texts.new('Lunar_DEM_Report.json');t.clear()
        t.write(json.dumps(dict(available_sources=catalog.at(p.latitude,p.longitude),last_inspection_or_build=json.loads(p.dem_report),download_details=json.loads(p.dem_download_report)),indent=2))
        if c.area:c.area.type='TEXT_EDITOR';c.area.spaces.active.text=t
        self.report({'INFO'},'DEM report saved in Lunar_DEM_Report.json text block');return {'FINISHED'}

class LUNAR_PT_main(bpy.types.Panel):
    bl_label='Lunar Terrain';bl_idname='LUNAR_PT_main';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Lunar'
    def draw(self,c):
        p=c.scene.lunar_terrain;l=self.layout;col=l.column();col.enabled=not p.busy
        row=col.row(align=True);row.operator('lunar.atlas',icon='WORLD');row.operator('lunar.import_location',text='Import Location',icon='IMPORT')
        if p.site in sites.POLAR_SITES:col.label(text='Polar Hapke: Apollo analogue',icon='INFO')
        col.prop(p,'site');col.operator('lunar.apply_preset',icon='WORLD');col.prop(p,'latitude');col.prop(p,'longitude');col.separator();col.operator('lunar.build',icon='MESH_GRID');col.prop(p,'download_first')
        if p.site=='CH3':col.operator('lunar.photo_references',icon='IMAGE_DATA')
        l.label(text=p.status[:70],icon='TIME' if p.busy else 'INFO')
        if p.busy:l.label(text='Esc cancels between stages / strips')
class Subpanel:
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Lunar';bl_parent_id='LUNAR_PT_main'
    def fields(self,c,names):
        col=self.layout.column();col.enabled=not c.scene.lunar_terrain.busy;col.use_property_split=True;col.use_property_decorate=False
        for name in names:col.prop(c.scene.lunar_terrain,name)
        return col
class LUNAR_PT_dem(Subpanel,bpy.types.Panel):
    bl_idname='LUNAR_PT_dem';bl_label='DEM and spatial resolution'
    def draw(self,c):
        p=c.scene.lunar_terrain;best=catalog.best(p.latitude,p.longitude)
        self.layout.label(text=f"Catalog at origin: {best['posting_m']:.3g} m grid")
        self.layout.label(text=best['title'])
        col=self.fields(c,['native_radius','dem_budget_mb','outer_radius','detail_radius','mesh_spacing','focus_mode','curvature','custom_dem'])
        op=col.operator('lunar.build',text='Download DEM for this location',icon='IMPORT');op.download_only=True
        col.operator('lunar.inspect_dem',icon='VIEWZOOM');col.operator('lunar.dem_map',icon='WORLD');col.operator('lunar.dem_report',icon='TEXT')
        col.label(text='Mesh finer than the DEM adds procedural detail')
        col.label(text='Grid spacing is not effective resolving power')
        for line in p.dem_status.split('|'):col.label(text=line.strip())
        if p.download_status:col.label(text=p.download_status)
class LUNAR_PT_ground(Subpanel,bpy.types.Panel):
    bl_idname='LUNAR_PT_ground';bl_label='Rocks and worn craters'
    def draw(self,c):self.fields(c,['rock_coverage','min_rock','micro_density','max_rocks','crater_density','micro_craters','crater_depth','roughness','seed']).operator('lunar.update_rocks',icon='MOD_DISPLACE')
class LUNAR_PT_light(Subpanel,bpy.types.Panel):
    bl_idname='LUNAR_PT_light';bl_label='Sun and Hapke opposition';bl_options={'DEFAULT_CLOSED'}
    def draw(self,c):
        col=self.fields(c,['sun_azimuth','sun_elevation','sun_diameter','sun_energy','visible_sun'])
        col.separator();col.prop(c.scene.lunar_terrain,'appearance');col.operator('lunar.apply_appearance',icon='MATERIAL')
        for name in ['exposure','soil_tint','albedo_variation','rock_albedo_ratio','regolith_relief','opposition']:col.prop(c.scene.lunar_terrain,name)
        col.operator('lunar.update_light',icon='LIGHT_SUN')
class LUNAR_PT_photometry(Subpanel,bpy.types.Panel):
    bl_idname='LUNAR_PT_photometry';bl_label='Advanced Hapke parameters';bl_options={'DEFAULT_CLOSED'}
    def draw(self,c):
        col=self.fields(c,['single_scattering_albedo','phase_b','phase_c','photometric_roughness','shoe_amplitude','shoe_width','cboe_amplitude','cboe_width'])
        col.operator('lunar.load_photometry',icon='WORLD');col.operator('lunar.update_light',icon='MATERIAL')
        col.label(text='Regional 566 nm fits: 70°S–70°N')

class LUNAR_PT_scene(Subpanel,bpy.types.Panel):
    bl_idname='LUNAR_PT_scene';bl_label='Camera and outpost';bl_options={'DEFAULT_CLOSED'}
    def draw(self,c):self.fields(c,['camera_height','camera_heading','camera_pitch','camera_lens','include_outpost','setup_scene','samples']).operator('lunar.clear',icon='TRASH')
CLASSES=(LUNAR_PG_settings,LUNAR_OT_inspect_dem,LUNAR_OT_dem_map,LUNAR_OT_photo_references,LUNAR_OT_atlas,LUNAR_OT_import_location,LUNAR_OT_dem_report,LUNAR_OT_preset,LUNAR_OT_appearance,LUNAR_OT_photometry,LUNAR_OT_build,LUNAR_OT_light,LUNAR_OT_clear,LUNAR_OT_rocks,LUNAR_PT_main,LUNAR_PT_dem,LUNAR_PT_ground,LUNAR_PT_light,LUNAR_PT_photometry,LUNAR_PT_scene)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.lunar_terrain=PointerProperty(type=LUNAR_PG_settings)
    # Registration runs with restricted bpy.data/context. Runtime flags have
    # property defaults; scene access belongs in operators after registration.
def unregister():
    if _active_job:_active_job._finish(bpy.context,True)
    del bpy.types.Scene.lunar_terrain
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
