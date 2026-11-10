"""Regional photometric priors and independent display appearance presets."""
from pathlib import Path
import math
import numpy as np
PARAMETER_FIELDS={'w':'single_scattering_albedo','b':'phase_b','c':'phase_c','theta':'photometric_roughness','B_SH0':'shoe_amplitude','h_SH':'shoe_width','B_CB0':'cboe_amplitude','h_CB':'cboe_width'}
BANDS=('w','b','c','B_CB0','h_CB','B_SH0','h_SH','theta','phi')
LOOKS={'APOLLO':dict(latitude=20.1908,longitude=30.7717,exposure=4.4,soil_tint=(.95,.95,.95),albedo_variation=.10,rock_albedo_ratio=1.08),
'CHANGE':dict(latitude=-41.6385,longitude=206.0148,exposure=2.8,soil_tint=(1.,.90,.74),albedo_variation=.08,rock_albedo_ratio=1.08),
# Regional LROC physics and an independent image-reference colour balance.
# The cool tint is an appearance choice, not a measured blue soil spectrum.
'BLUEGHOST':dict(latitude=18.5623,longitude=61.8103,exposure=4.7,soil_tint=(.50,.64,1.),albedo_variation=.06,rock_albedo_ratio=1.04),
# NavCam is grayscale; anaglyph red/cyan is a stereo display, not soil colour.
'CH3':dict(latitude=-69.373,longitude=32.319,exposure=1.8,soil_tint=(.92,.92,.92),albedo_variation=.06,rock_albedo_ratio=1.04,regolith_relief=2.2)}
def parameters_at(latitude,longitude):
    if not -70<latitude<70:raise ValueError('LROC map covers 70°S–70°N; use an explicit analogue for polar terrain. Existing parameters retained.')
    with np.load(Path(__file__).parent/'data/photometry/WAC_Hapke_566nm.npz',allow_pickle=False) as pack:
        values=pack['parameters'][:,int(math.floor(70-latitude)),int(math.floor(longitude%360))]
    p=dict(zip(BANDS,map(float,values)))
    if not all(math.isfinite(v) and abs(v)<1e10 for v in p.values()) or not 0<p['w']<1:raise ValueError('No valid regional fit in this cell; current parameters retained.')
    if p['phi']!=0 or p['B_CB0']!=0:raise ValueError('This cell needs a different porosity/CBOE variant.')
    bounds={'w':(.001,.99),'b':(0,.95),'c':(-1,1),'B_SH0':(0,5),'h_SH':(.0001,1),'theta':(0,45)}
    if any(not lo<=p[k]<=hi for k,(lo,hi) in bounds.items()):raise ValueError('This regional fit exceeds supported parameter limits; existing values retained.')
    return p
def set_photometry(settings,latitude,longitude):
    p=parameters_at(latitude,longitude)
    for key,field in PARAMETER_FIELDS.items():setattr(settings,field,p[key])
def apply(settings,look):
    p=LOOKS[look];set_photometry(settings,p['latitude'],p['longitude'])
    for key in ('exposure','soil_tint','albedo_variation','rock_albedo_ratio'):setattr(settings,key,p[key])
    settings.regolith_relief=p.get('regolith_relief',1.)
    settings.opposition=1.;settings.appearance=look
