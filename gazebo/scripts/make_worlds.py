"""Create Gazebo worlds using the exporter manifest; no Blender dependency."""
from copy import deepcopy
from pathlib import Path
import json,xml.etree.ElementTree as E
def add(p,t,s=None,**kw):
    e=E.SubElement(p,t,kw)
    if s is not None:e.text=str(s)
    return e
def write(t,p):E.indent(t);E.ElementTree(t).write(p,encoding='utf-8',xml_declaration=True)
def main(root):
    d=json.loads((root/'export_manifest.json').read_text());model=d['model_id'];world=model.removesuffix('_terrain')
    s=E.Element('sdf',version='1.10');w=add(s,'world',name=world)
    add(w,'gravity','0 0 -1.62');p=add(w,'physics',name='lunar_1ms',type='ignored');add(p,'max_step_size',.001);add(p,'real_time_factor',1)
    for f,n in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('sensors','Sensors')]:
        p=add(w,'plugin',filename=f'gz-sim-{f}-system',name=f'gz::sim::systems::{n}')
        if n=='Sensors':add(p,'render_engine','ogre2')
    scene=add(w,'scene');add(scene,'ambient','0.008 0.008 0.008 1');add(scene,'background','0 0 0 1');add(scene,'shadows','true');add(scene,'grid','false')
    light=add(w,'light',name='sun',type='directional');add(light,'direction',' '.join(map(str,d['sun_ray_direction'])));add(light,'diffuse','1 1 1 1');add(light,'specular','0 0 0 1');add(light,'intensity',d['source_sun_energy']);add(light,'cast_shadows','true')
    add(add(w,'include'),'uri','model://'+model)
    m=add(w,'model',name=world+'_camera');add(m,'static','true');pose=' '.join(map(str,d['camera_pose_sdf']));add(m,'pose',pose)
    sensor=add(add(m,'link',name='camera_link'),'sensor',name='surface_camera',type='camera');add(sensor,'always_on','true');add(sensor,'update_rate',10);add(sensor,'topic','/'+world+'/camera/image')
    c=add(sensor,'camera');add(c,'horizontal_fov',d['camera_hfov']);im=add(c,'image');add(im,'width',d['camera_image_size'][0]);add(im,'height',d['camera_image_size'][1]);add(im,'format','R8G8B8');clip=add(c,'clip');add(clip,'near',.05);add(clip,'far',30000)
    gui=add(w,'gui',fullscreen='false');p=add(gui,'plugin',filename='MinimalScene',name='3D View');gg=add(p,'gz-gui');add(gg,'title','3D View');add(gg,'property','false',key='showTitleBar',type='bool');add(gg,'property','docked',key='state',type='string')
    add(p,'engine','ogre2');add(p,'scene','scene');add(p,'camera_pose',pose);cl=add(p,'camera_clip');add(cl,'near',.05);add(cl,'far',30000);add(p,'background_color','0 0 0 1');add(p,'ambient_light','0.008 0.008 0.008 1')
    for f in ['GzSceneManager','InteractiveViewControl','CameraTracking','EntityContextMenuPlugin','WorldControl','WorldStats']:
        p=add(gui,'plugin',filename=f,name=f);g=add(p,'gz-gui');add(g,'property','floating',key='state',type='string');add(g,'property','false',key='showTitleBar',type='bool')
    write(s,root/'worlds'/f'{world}.sdf');test=deepcopy(s);tw=test.find('world');tw.set('name',world+'_test')
    for i,site in enumerate(d['test_probe_sites']):
        m=add(tw,'model',name=f'drop_probe_{i}');x,y=site['xy'];add(m,'pose',f'{x} {y} {site["collision_z"]+1.1} 0 0 0');li=add(m,'link',name='body');ine=add(li,'inertial');add(ine,'mass',1);it=add(ine,'inertia')
        for axis in ['ixx','iyy','izz']:add(it,axis,.006666666666666667)
        for tag in ['collision','visual']:
            sh=add(li,tag,name='box');add(add(add(sh,'geometry'),'box'),'size','.2 .2 .2')
            if tag=='collision':
                ode=add(add(add(sh,'surface'),'friction'),'ode');add(ode,'mu',.8);add(ode,'mu2',.8)
    free=deepcopy(tw.find("model[@name='drop_probe_0']"));free.set('name','freefall_probe');free.find('pose').text=f"{d['freefall_x_m']} 0 10 0 0 0";tw.append(free)
    write(test,root/'worlds'/f'{world}_test.sdf')
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package',type=Path)
    main(parser.parse_args().package.resolve())
