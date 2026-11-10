"""Render catalog footprints and embed them in an offline coordinate lookup."""
from pathlib import Path
import json,sys,types,math,base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from matplotlib.patches import PathPatch,Patch
from matplotlib.path import Path as MPath
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'lunar_terrain/data'
pkg=types.ModuleType('lunar_terrain');pkg.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=pkg
from lunar_terrain import remote_dem as rd
def main():
    raw=(DATA/'dem_catalog.geojson').read_text();data=json.loads(raw)
    colors={2:'#6c3ab0',3:'#316ac5',4:'#168baf',5:'#3e9971',6:'#c49525',7:'#c06d39'}
    sites=[('Apollo 17',20.1908,30.7717),('Chang’e-6',-41.6385,206.0148),('Connecting Ridge',-89.438788,222.844980)]
    fig=plt.figure(figsize=(16,11),facecolor='#f8f9fa');gs=fig.add_gridspec(2,3,height_ratios=[1.55,1],left=.065,right=.97,top=.84,bottom=.20,hspace=.36,wspace=.25)
    world=fig.add_subplot(gs[0,:]);south=fig.add_subplot(gs[1,0]);apollo=fig.add_subplot(gs[1,1]);change=fig.add_subplot(gs[1,2])
    a=np.load(DATA/'LOLA_global_16ppd.npz')['elevation'][::4,::4].astype(float);a=np.roll(a,a.shape[1]//2,axis=1)
    shade=LightSource(315,40).hillshade(a*.5,vert_exag=6,dx=rd.MPD/4,dy=rd.MPD/4)
    world.imshow(.65+.24*shade,cmap='gray',vmin=0,vmax=1,extent=(-180,180,-90,90),aspect='auto')
    for ax in (world,south,apollo,change):ax.set_facecolor('#bcc6cf');ax.tick_params(labelsize=10);ax.grid(alpha=.2);ax.set_axisbelow(True)
    def transform(ax,x,y):
        if ax==world:return x,y
        if ax==south:
            px,py=rd.project(dict(projection='south_polar'),y,x);return px/1000,py/1000
        lat,lon=(20.1908,30.7717) if ax==apollo else (-41.6385,206.0148)
        return ((x-lon+180)%360-180)*rd.MPD*math.cos(math.radians(lat))/1000,(y-lat)*rd.MPD/1000
    for f in sorted(data['features'],key=lambda f:f['properties']['posting_m'],reverse=True):
        g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        for poly in polys:
            for ax in (world,south,apollo,change):
                vertices=[];codes=[]
                for ring in poly:
                    ar=np.array(ring);x,y=transform(ax,ar[:,0],ar[:,1]);vertices.extend(zip(x,y));codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(x)-2)+[MPath.CLOSEPOLY])
                if vertices:ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=colors[int(f['properties']['posting_m'])],edgecolor='none',clip_on=True))
    world.set(xlim=(-180,180),ylim=(-90,90),xlabel='Longitude (° east; negative values west)',ylabel='Latitude (° north)');world.set_xticks(np.arange(-180,181,60));world.set_yticks(np.arange(-90,91,30))
    for name,lat,lon in sites:
        x=(lon+180)%360-180;world.plot(x,lat,'o',color='white',markeredgecolor='#111',markersize=5,zorder=9)
        world.annotate(name,(x,lat),xytext=(6,9 if lat>-80 else 12),textcoords='offset points',fontsize=10,color='#111',bbox=dict(facecolor='white',alpha=.85,edgecolor='none',pad=2))
    south.set(title='South pole • 150 km across',xlim=(-75,75),ylim=(-75,75),xlabel='Polar X (km)',ylabel='Polar Y (km)');south.set_aspect('equal')
    for ax,(name,lat,lon) in [(apollo,sites[0]),(change,sites[1])]:ax.set(title=name+' • 50 km across',xlim=(-25,25),ylim=(-25,25),xlabel='East from site (km)',ylabel='North from site (km)');ax.set_aspect('equal')
    for ax,(_,lat,lon) in [(south,sites[2]),(apollo,sites[0]),(change,sites[1])]:
        x,y=transform(ax,np.array([lon]),np.array([lat]));ax.plot(x,y,'o',markerfacecolor='white',markeredgecolor='#111',markersize=6,zorder=9)
    fig.text(.065,.955,'Lunar DEM resolution coverage',fontsize=26,weight='bold',color='#142333')
    fig.text(.065,.921,'Finest published grid in supported public catalogs • snapshot '+data['snapshot_date'],fontsize=14,color='#374b5f')
    handles=[Patch(facecolor=colors[p],label=f'{p} m') for p in colors]+[Patch(facecolor='#bcc6cf',label='7.403 m nominal global grid')]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.06,.907),ncol=7,frameon=False,fontsize=11,handlelength=1.3,columnspacing=1.5)
    fig.text(.065,.125,'Grid spacing is not effective resolution. JAXA’s 7.403 m grid uses ~10 m TC input, with fill, smoothing and resampling.',fontsize=11,color='#263746')
    fig.text(.065,.101,'Footprints can contain NoData. The add-on verifies actual cells and reports fallback grids. Fine mesh does not add measured terrain.',fontsize=11,color='#263746')
    fig.text(.065,.062,f"Sources: 660 LROC NAC footprints (release through {data['nac_release_through']}); 27 NASA adjusted LOLA products; JAXA SLDEM2013.",fontsize=10,color='#465768')
    fig.text(.065,.04,'Global relief: LOLA 16 ppd. Local insets use site-centred coordinates; polar inset uses lunar stereographic projection. Isolated research and surface DEMs are not exhaustive.',fontsize=9.5,color='#465768')
    output=DATA/'Lunar_DEM_Map.png';fig.savefig(output,dpi=150);plt.close(fig)
    html=(ROOT/'tools/dem_map_template.html').read_text().replace('__IMAGE__',base64.b64encode(output.read_bytes()).decode()).replace('__DATA__',raw)
    (DATA/'Lunar_DEM_Map.html').write_text(html);print('MAP READY',flush=True)
if __name__=='__main__':main()
