"""Original editable rover and outpost models; no downloaded commercial meshes."""
import bpy,math,random
import numpy as np
from mathutils import Vector

CURRENT=None
PARENT=None
M={}
TEMPLATES={}

def use(collection,parent=None):
    global CURRENT,PARENT
    CURRENT,PARENT=collection,parent

def adopt(obj,name,mat=None):
    obj.name=name
    for c in list(obj.users_collection):c.objects.unlink(obj)
    CURRENT.objects.link(obj)
    if PARENT:obj.parent=PARENT
    if mat:obj.data.materials.append(mat if not isinstance(mat,str) else M[mat])
    return obj

def bevel(obj,width=.04,segments=3):
    mod=obj.modifiers.new('Machined edge radii','BEVEL');mod.width=width;mod.segments=segments
    mod=obj.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return obj

def cube(name,loc,dim,mat,bev=.04,rot=None):
    dx,dy,dz=(d/2 for d in dim)
    verts=[(-dx,-dy,-dz),(-dx,-dy,dz),(-dx,dy,-dz),(-dx,dy,dz),
           (dx,-dy,-dz),(dx,-dy,dz),(dx,dy,-dz),(dx,dy,dz)]
    o=poly(name,verts,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],mat)
    o.location=loc
    if rot:o.rotation_euler=rot
    if bev:bevel(o,bev)
    return o

def uv(name,loc,scale,mat,segments=32,rings=20):
    key=(segments,rings)
    if key not in TEMPLATES:
        verts=[];faces=[]
        for i in range(rings+1):
            th=math.pi*(i+.0001)/(rings+.0002)
            for j in range(segments):
                a=2*math.pi*j/segments
                verts.append((math.sin(th)*math.cos(a),math.sin(th)*math.sin(a),math.cos(th)))
        for i in range(rings):
            for j in range(segments):
                a=i*segments+j;b=i*segments+(j+1)%segments
                faces.append((a,a+segments,b+segments,b))
        TEMPLATES[key]=(verts,faces)
    verts,faces=TEMPLATES[key]
    o=poly(name,verts,faces,mat);o.location=loc;o.scale=scale
    for p in o.data.polygons:p.use_smooth=True
    return o

def cyl(name,loc,radius,depth,mat,axis='Z',verts=48,bev=.025):
    coords=[(radius*math.cos(2*math.pi*j/verts),radius*math.sin(2*math.pi*j/verts),z)
            for z in [-depth/2,depth/2] for j in range(verts)]
    faces=[(j,(j+1)%verts,(j+1)%verts+verts,j+verts) for j in range(verts)]
    faces += [tuple(range(verts-1,-1,-1)),tuple(range(verts,2*verts))]
    o=poly(name,coords,faces,mat);o.location=loc
    if axis=='X':o.rotation_euler[1]=math.pi/2
    if axis=='Y':o.rotation_euler[0]=math.pi/2
    for p in o.data.polygons:p.use_smooth=(len(p.vertices)==4)
    if bev:bevel(o,bev,2)
    return o

def torus(name,loc,radius,tube,mat,axis='Z',major_segments=64,minor_segments=12):
    v=[];f=[]
    for i in range(major_segments):
        a=2*math.pi*i/major_segments
        for j in range(minor_segments):
            b=2*math.pi*j/minor_segments
            v.append(((radius+tube*math.cos(b))*math.cos(a),(radius+tube*math.cos(b))*math.sin(a),tube*math.sin(b)))
    for i in range(major_segments):
        for j in range(minor_segments):
            a=i*minor_segments+j;b=((i+1)%major_segments)*minor_segments+j
            f.append((a,b,((i+1)%major_segments)*minor_segments+(j+1)%minor_segments,i*minor_segments+(j+1)%minor_segments))
    o=poly(name,v,f,mat);o.location=loc
    if axis=='X':o.rotation_euler[1]=math.pi/2
    if axis=='Y':o.rotation_euler[0]=math.pi/2
    for p in o.data.polygons:p.use_smooth=True
    return o

def rod(name,a,b,r,mat):
    v=Vector(b)-Vector(a);mid=(Vector(a)+Vector(b))/2
    o=cyl(name,mid,r,v.length,mat,verts=16,bev=0)
    o.rotation_mode='QUATERNION';o.rotation_quaternion=v.to_track_quat('Z','Y')
    return o

def poly(name,verts,faces,mat,bevel_width=0):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);CURRENT.objects.link(o)
    if PARENT:o.parent=PARENT
    mesh.materials.append(M[mat] if isinstance(mat,str) else mat)
    if bevel_width:bevel(o,bevel_width)
    return o

def text(name,body,loc,size,mat,rot=(math.pi/2,0,0),align='CENTER'):
    data=bpy.data.curves.new(name,'FONT');data.body=body;data.size=size;data.align_x=align
    data.extrude=.0008;data.bevel_depth=.0003
    obj=bpy.data.objects.new(name,data);CURRENT.objects.link(obj);obj.location=loc;obj.rotation_euler=rot
    if PARENT:obj.parent=PARENT
    data.materials.append(M[mat]);return obj

def materials():
    settings={'ceramic':((.72,.74,.74),.12,.29),'white':((.65,.67,.66),.04,.55),
       'metal':((.30,.34,.36),.86,.28),'dark':((.038,.046,.049),.6,.38),
       'rubber':((.013,.016,.018),.1,.75),'gold':((.53,.31,.07),.85,.3),
       'glass':((.07,.115,.15),.85,.12),'visor':((.39,.24,.075),.94,.10),
       'blue':((.018,.12,.26),.40,.27),'solar':((.018,.037,.08),.82,.23),
       'orange':((.52,.105,.025),.28,.4),'red':((.60,.012,.018),.04,.4),
       'led':((.68,.78,.86),.2,.2)}
    for name,(color,metal,rough) in settings.items():
        ma=bpy.data.materials.new('Hardware • '+name);ma.diffuse_color=(*color,1)
        p=ma.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
        p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
        if name=='led':
            p.inputs['Emission Color'].default_value=(.65,.79,1,1);p.inputs['Emission Strength'].default_value=1
        if name in ['gold','white']:
            ns=ma.node_tree.nodes.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=100 if name=='gold' else 220
            ns.inputs['Detail'].default_value=3
            bump=ma.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22
            bump.inputs['Distance'].default_value=.018 if name=='gold' else .0007
            ma.node_tree.links.new(ns.outputs['Fac'],bump.inputs['Height']);ma.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
        M[name]=ma

def root(name,loc,collection,yaw=0):
    o=bpy.data.objects.new(name,None);collection.objects.link(o);o.location=loc;o.rotation_euler[2]=yaw
    o.empty_display_type='CUBE';o.empty_display_size=.6;return o

def dish(name,base,radius=1.2):
    x,y,z=base
    rod(name+' mast',(x,y,z),(x,y,z+2.0),.075,'metal')
    # Paraboloid with a real concave profile; normal tilted up from the horizon.
    nr,na=12,64;v=[];f=[]
    tilt=math.radians(65)
    for i in range(nr+1):
        rr=radius*(i+.002)/(nr+.002)
        for j in range(na):
            a=2*math.pi*j/na;px=rr*math.cos(a);py=rr*math.sin(a);pz=.35*(rr/radius)**2
            v.append((x+px,y+py*math.cos(tilt)-pz*math.sin(tilt),z+2+py*math.sin(tilt)+pz*math.cos(tilt)))
    for i in range(nr):
        for j in range(na):
            a=i*na+j;b=i*na+(j+1)%na;c=b+na;d=a+na;f.append((a,b,c,d))
    o=poly(name+' parabolic reflector',v,f,'ceramic')
    for p in o.data.polygons:p.use_smooth=True
    sol=o.modifiers.new('Reflector shell','SOLIDIFY');sol.thickness=.026
    feed=(x,y-.55,z+2.5)
    for a in [0,2*math.pi/3,4*math.pi/3]:
        rr=radius*.92;point=(x+rr*math.cos(a),y+rr*math.sin(a)*math.cos(tilt)-.29*math.sin(tilt),z+2+rr*math.sin(a)*math.sin(tilt)+.29*math.cos(tilt))
        rod(name+' feed support',point,feed,.014,'dark')
    uv(name+' receiver',feed,(.10,.10,.14),'dark')

def rover(collection,surface):
    rx,ry=-7,-8
    ground=float(surface.height(rx,ry))
    r=root('ROVER • move this assembly', (rx,ry,ground), collection,math.radians(-12))
    r['Design']='Original visual approximation inspired by JAXA/Toyota March 2025 Lunar Cruiser; not production CAD.'
    r['nominal_envelope_m']='4.6 wide × 7.0 long × 5.8 including antenna'
    use(collection,r)
    cube('Belly chassis',(0,.1,1.40),(3.4,6.6,.48),'dark',.12)
    cube('Pressurized cabin',(0,-.15,2.97),(3.65,5.9,2.30),'ceramic',.32)
    cube('Rear service enclosure',(0,2.25,3.15),(3.45,1.63,2.03),'white',.20)
    cube('Thermal blanket roof',(0,.05,4.10),(2.90,4.6,.17),'white',.07)
    # Sloped face shell.
    verts=[(-1.72,-3.25,2.08),(1.72,-3.25,2.08),(-1.72,-3.18,3.08),(1.72,-3.18,3.08),
       (-1.34,-2.74,4.00),(1.34,-2.74,4.00),(-1.55,-2.55,2.08),(1.55,-2.55,2.08)]
    poly('Faceted cab nose',verts,[(0,1,3,2),(2,3,5,4),(0,2,4,6),(1,7,5,3),(4,5,7,6),(0,6,7,1)],'ceramic',.035)
    # Forward windows in upper and lower bands.
    for zlo,zhi,mat in [(3.12,3.49,'glass'),(2.69,3.04,'visor')]:
        ylo=-3.19+(zlo-3.08)*.478-.018;yhi=-3.19+(zhi-3.08)*.478-.018
        widthlo=1.51-(zlo-3.08)*.28;widthhi=1.51-(zhi-3.08)*.28
        for a,b in [(-1,-.34),(-.32,.32),(.34,1)]:
            poly('Cab window',[(a*widthlo,ylo,zlo),(b*widthlo,ylo,zlo),(b*widthhi,yhi,zhi),(a*widthhi,yhi,zhi)],[(0,1,2,3)],mat)
    cube('Front bumper',(0,-3.38,1.98),(3.82,.30,.32),'metal',.055)
    cube('Front equipment hatch',(0,-3.32,2.35),(1.64,.12,.43),'dark',.03)
    text('Rover front wordmark','LUNAR CRUISER',(0,-3.545,2.01),.115,'ceramic')
    for side in [-1,1]:
        sx=side*1.88
        cube('Side radiator backing',(sx,.40,1.91),(.12,5.45,.74),'dark',.035)
        for j in range(32):
            cube('Radiator fin',(sx+side*.071,-2.20+j*.166,1.93),(.034,.024,.62),'metal',.006)
        for y in [-2.05,0,2.12]:
            wx=side*2.03
            yaw=r.rotation_euler[2]
            gx=rx+math.cos(yaw)*wx-math.sin(yaw)*y
            gy=ry+math.sin(yaw)*wx+math.cos(yaw)*y
            z=float(surface.height(gx,gy))-ground+.86
            tire=torus('Airless mesh tyre',(wx,y,z),.70,.145,'rubber','X',80,16)
            tire.scale.z=1.8
            cyl('Wheel inner drum',(wx,y,z),.62,.42,'dark','X')
            for offset in [-.265,.265]:
                torus('Wheel edge ring',(wx+offset,y,z),.64,.026,'metal','X')
            exterior=wx+side*.30
            for j in range(12):
                a=j*2*math.pi/12
                rod('Wheel radial spoke',(exterior,y+.17*math.sin(a),z+.17*math.cos(a)),
                    (exterior,y+.59*math.sin(a+.11),z+.59*math.cos(a+.11)),.033,'metal')
            cyl('Hub cover',(exterior+side*.018,y,z),.20,.075,'metal','X')
            cyl('Hub center',(exterior+side*.061,y,z),.10,.025,'dark','X')
            for j in range(48):
                a=j*2*math.pi/48
                cube('Tyre grouser',(wx,y+.836*math.sin(a),z+.836*math.cos(a)),(.52,.072,.032),
                     'metal',.005,(-a,0,0))
            rod('Lower suspension arm',(side*1.24,y-.62,1.30),(wx,y,z+.04),.090,'dark')
            rod('Upper suspension link',(side*1.37,y+.46,1.50),(wx,y,z+.22),.065,'metal')
            rod('Shock absorber',(side*1.55,y+.20,1.72),(side*1.90,y+.07,z+.13),.075,'metal')
            rod('Shock bellows',(side*1.55,y+.20,1.72),(side*1.73,y+.13,1.38),.099,'orange')
        cube('Corner equipment pod',(side*1.86,-2.80,2.40),(.60,.70,.57),'ceramic',.10)
        for j in range(3):
            lx=side*(.88+j*.34)
            cyl('Headlamp housing',(lx,-2.995,3.68),.143,.12,'dark','Y')
            cyl('Headlamp lens',(lx,-3.065,3.68),.118,.015,'led','Y')
        cyl('Front auxiliary lamp',(side*1.52,-3.565,2.02),.135,.035,'led','Y')
        # Small fasteners and side window.
        for yy in [-1.9,-.9,.2,1.2]:
            for zz in [2.48,3.83]:uv('Panel fastener',(side*1.828,yy,zz),(.014,.026,.026),'metal',12,8)
        cube('Side navigation window',(side*1.839,-1.85,3.30),(.025,.68,.36),'glass',.05)
        cube('Japan flag plate',(side*1.85,-1.18,3.38),(.025,.36,.23),'white',.006)
        cyl('Japan flag disc',(side*1.868,-1.18,3.38),.068,.008,'red','X',32,0)
    # Rear ladder and access door.
    cube('Rear hatch',(0,3.09,3.05),(1.5,.10,1.8),'dark',.12)
    for x in [-.58,.58]:rod('Rear ladder rail',(x,3.28,.62),(x,3.28,2.22),.030,'metal')
    for z in np.arange(.72,2.2,.25):rod('Ladder rung',(-.58,3.28,z),(.58,3.28,z),.028,'metal')
    for x,y in [(-1.18,-1.92),(1.20,-1.9),(.9,2.2)]:
        cyl('Antenna mount',(x,y,4.14),.095,.19,'dark')
        rod('Whip antenna',(x,y,4.18),(x,y,4.98),.015,'metal')
    dish('Rover high-gain',(-.35,.15,3.0),.48)
    # Dish mast is shortened into the roof body; base of parabola at z=5.
    cube('Roof lidar',(0,-2.0,4.22),(.65,.42,.21),'dark',.035)
    for x in [-.95,.95]:
        rod('Roof luggage rail',(x,-1.4,4.30),(x,1.3,4.30),.03,'metal')
    return r

def habitat(collection,surface,cx,cy,length,label):
    r=root('HABITAT '+label+' • assembly',(cx,cy,float(surface.height(cx,cy))),collection)
    use(collection,r)
    z=3.15
    cyl('Pressure vessel '+label,(0,0,z),2.40,length,'white','X',64,.13)
    for x in [-length/2,length/2]:
        uv('Pressure dome',(x,0,z),(.68,2.38,2.38),'ceramic',48,24)
        torus('End structural ring',(x,0,z),2.39,.065,'metal','X')
    for x in np.arange(-length/2+.7,length/2,.95):
        torus('Thermal restraint band',(x,0,z),2.414,.022,'metal','X',48,8)
    for x in [-length*.32,length*.32]:
        for y in [-1.85,1.85]:
            # Feet conform to DEM rather than hovering over the sloped ground.
            gz=float(surface.height(cx+x,cy+y))-float(surface.height(cx,cy))
            rod('Adjustable support leg',(x,y,1.85),(x,y,gz+.12),.13,'metal')
            cyl('Circular ground foot',(x,y,gz+.055),.43,.10,'dark')
            rod('Diagonal landing brace',(x,y,1.32),(x+.65,y,gz+.22),.055,'metal')
    for x in np.arange(-length*.3,length*.4,2.4):
        cube('Recessed observation port',(x,-2.38,z+.35),(1.1,.12,.62),'dark',.12)
        cube('Blue observation glazing',(x,-2.459,z+.35),(.89,.02,.43),'glass',.07)
    text('Habitat designation',label,(0,-2.455,2.7),.36,'dark')
    text('Habitat subtitle','SOUTH POLE  /  SURFACE SYSTEMS',(0,-2.457,2.27),.13,'dark')
    # Central blue band and numbered end airlock.
    torus('Blue identity ring',(length*.38,0,z),2.432,.078,'blue','X')
    cyl('Airlock flange',(length/2+.63,0,z),1.10,.25,'metal','X')
    cyl('Airlock pressure door',(length/2+.78,0,z),.94,.16,'ceramic','X')
    torus('Airlock gasket',(length/2+.87,0,z),.84,.022,'dark','X')
    cube('Door window',(length/2+.886,-.08,z+.28),(.022,.43,.41),'glass',.05)
    return r

def base(collection,surface):
    habitat(collection,surface,12,28,13,'HABITAT 01')
    habitat(collection,surface,-5,42,10,'SCIENCE 02')
    r=root('BASE • utilities',(0,0,0),collection);use(collection,r)
    # Flexible connecting corridor between modules.
    za=float(surface.height(10,31))+2.15
    cyl('Pressurized transfer tunnel',(10,33,za),1.1,5,'white','Y')
    for y in np.arange(31,35.1,.45):torus('Tunnel hoop',(10,y,za),1.105,.032,'metal','Y',40,8)
    cyl('Cross-gallery',(3,35,za),1.1,14,'white','X')
    for x in np.arange(-4,10,.55):torus('Cross-gallery hoop',(x,35,za),1.105,.03,'metal','X',40,8)
    cyl('Science entrance tunnel',(-4,38,za),1.1,6,'white','Y')
    for x in [-4,10]:uv('Tunnel elbow',(x,35,za),(1.13,1.13,1.13),'white')
    # Airlock ramp and guardrails.
    z=float(surface.height(12,28))
    cube('Airlock landing',(20.2,28,z+1.8),(2.3,2.5,.22),'metal',.035)
    for yy in [26.85,29.15]:
        rod('Landing handrail',(19.1,yy,z+2.8),(21.3,yy,z+2.8),.035,'orange')
        for xx in [19.1,21.3]:rod('Handrail upright',(xx,yy,z+1.9),(xx,yy,z+2.8),.030,'metal')
    for i in range(7):
        xx=21.4+i*.40;zz=z+1.7-i*.22
        cube('Airlock step',(xx,28,zz),(.45,2.12,.12),'metal',.015)
    # Polar solar arrays: steeply tilted to intercept grazing sunlight.
    for idx,(x,y) in enumerate([(29,36),(33,42),(28,50)]):
        gz=float(surface.height(x,y))
        for dx in [-2.5,2.5]:
            rod('Solar pedestal',(x+dx,y,gz),(x+dx,y,gz+3.4),.09,'metal')
            cyl('Solar anchor',(x+dx,y,gz+.08),.35,.16,'dark')
        pr=root(f'SOLAR ARRAY {idx+1}',(x,y,gz+3.4),collection,math.radians(-12))
        use(collection,pr)
        # Panel lies in local XY and is tilted about X toward the horizon.
        pr.rotation_euler[0]=math.radians(78)
        cube('Panel support',(0,0,0),(6.3,3.6,.13),'metal',.02)
        for ix in range(10):
            for iy in range(6):
                cube('Photovoltaic tile',(-2.80+ix*.625,-1.46+iy*.584,.082),(.59,.55,.014),'solar',.008)
        for xx in np.arange(-3,3.1,.63):cube('Panel conductor',(xx,0,.096),(.012,3.4,.009),'metal',0)
        use(collection,r)
    # Communications platform and gold thermal insulation.
    x,y=-19,38;gz=float(surface.height(x,y))
    cyl('Comms thermal enclosure',(x,y,gz+1.25),.75,2.3,'gold',verts=8)
    for a in [0,2*math.pi/3,4*math.pi/3]:
        rod('Comms tripod',(x,y,gz+1.8),(x+2*math.cos(a),y+2*math.sin(a),float(surface.height(x+2*math.cos(a),y+2*math.sin(a)))+.1),.05,'metal')
    dish('Base communications',(x,y,gz+2.2),1.35)
    rod('Radio mast',(x+3,y+2,gz),(x+3,y+2,gz+8),.045,'metal')
    rod('Radio dipole',(x+1,y+2,gz+7.8),(x+5,y+2,gz+7.8),.022,'metal')
    # Cryogenic process / ISRU skid and radiator fins.
    x,y=-6,49;gz=float(surface.height(x,y))
    cube('ISRU equipment skid',(x,y,gz+.45),(7.0,3.0,.6),'dark',.08)
    for xx in [x-1.8,x,x+1.8]:
        cyl('Insulated storage tank',(xx,y,gz+1.8),.67,2.1,'white')
        uv('Tank top',(xx,y,gz+2.85),(.67,.67,.35),'ceramic')
        torus('Tank band',(xx,y,gz+2.1),.68,.035,'metal')
        rod('Tank plumbing',(xx,y-.1,gz+.75),(xx,y-1.7,gz+.75),.065,'metal')
    for x,y in [(23,44),(25,45),(27,46)]:
        gz=float(surface.height(x,y))
        cube('Vertical heat radiator',(x,y,gz+2.8),(2.0,.16,4.5),'ceramic',.025)
        for zz in np.arange(.7,4.9,.24):cube('Radiator channel',(x,y-.095,gz+zz),(1.8,.021,.027),'metal',0)
        rod('Radiator support',(x,y,gz),(x,y,gz+1),.10,'metal')
    for x,y in [(-3,21),(-1,22),(-4,24)]:
        gz=float(surface.height(x,y))
        cube('Cargo transport case',(x,y,gz+.58),(1.4,1.0,1.1),'white',.075)
        for dx in [-.45,.45]:cube('Cargo restraint',(x+dx,y,gz+.59),(.07,1.03,1.13),'orange',.012)
    # Low cable runs, tucked into the regolith.
    for points in [[(16,32),(23,33),(30,35)],[(8,45),(3,48),(-5,49)]]:
        for a,b in zip(points,points[1:]):
            rod('Surface utility cable',(*a,float(surface.height(*a))+.06),(*b,float(surface.height(*b))+.06),.035,'dark')
    return r

def astronaut(collection,surface,x=0,y=1):
    r=root('EVA • 1.85 m scale reference',(x,y,float(surface.height(x,y))),collection,math.radians(-20))
    use(collection,r)
    for s in [-1,1]:
        uv('EVA boot',(s*.15,-.06,.12),(.14,.23,.13),'dark')
        uv('EVA shin',(s*.15,0,.38),(.12,.12,.27),'white')
        uv('EVA knee',(s*.15,-.02,.61),(.135,.13,.13),'dark')
        uv('EVA upper leg',(s*.14,.015,.78),(.14,.15,.25),'white')
    uv('EVA torso',(0,0,1.12),(.30,.22,.35),'white')
    cube('EVA life support',(0,.27,1.20),(.48,.25,.52),'ceramic',.06)
    uv('EVA helmet',(0,-.005,1.66),(.255,.25,.255),'ceramic')
    uv('EVA gold visor',(0,-.185,1.68),(.213,.11,.163),'visor')
    for s in [-1,1]:
        uv('EVA shoulder',(s*.32,0,1.32),(.15,.15,.16),'white')
        rod('EVA upper arm',(s*.32,0,1.31),(s*.43,-.03,1.08),.095,'white')
        uv('EVA elbow',(s*.43,-.03,1.08),(.10,.10,.10),'dark')
        rod('EVA forearm',(s*.43,-.03,1.08),(s*.40,-.18,.92),.088,'white')
        uv('EVA glove',(s*.40,-.18,.91),(.088,.10,.105),'white')
        torus('Suit identification stripe',(s*.15,0,.49),.124,.018,'red')
    cube('Chest controls',(0,-.23,1.17),(.24,.06,.22),'dark',.025)
    return r
