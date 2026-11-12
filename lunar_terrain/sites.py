"""Documented polar reference coordinates, not confirmed touchdown fixes."""
CHECKED='2026-11-12'
DATA_BOOK='https://ntrs.nasa.gov/citations/20250002845'
POLAR_SITES={
 'MOONBASE':dict(name='Moon Base / Connecting Ridge',latitude=-89.4632,longitude=222.51,grid_m=2.,sun_elevation=1.4,sun_azimuth=285.,camera_heading=5.,source=DATA_BOOK,role='NASA R01 regional reference; Blue Moon Mark 1 target region',status='Permanent base site and touchdown coordinate not finalized'),
 'VIPER':dict(name='VIPER / Mons Mouton',latitude=-85.42088,longitude=31.6218,grid_m=5.,sun_elevation=5.8,sun_azimuth=0.,camera_heading=110.,source='https://doi.org/10.3847/PSJ/ae061a',role='Published primary mission-area center; not a touchdown fix',status='NASA lists Mons Mouton and delivery in 2027'),
 'NOBILE2':dict(name='South pole / Nobile Rim 2',latitude=-83.954,longitude=58.82206,grid_m=5.,sun_elevation=6.,sun_azimuth=0.,camera_heading=100.,source=DATA_BOOK,role='NASA DM2 regional reference point',status='Candidate region in NASA October 2024 shortlist; not an assigned landing site'),
 'MALAPERT':dict(name='South pole / Malapert Massif',latitude=-85.9948,longitude=359.76422,grid_m=4.,sun_elevation=5.3,sun_azimuth=0.,camera_heading=100.,source=DATA_BOOK,role='NASA R23 regional reference point; distinct from IM-1',status='Candidate region in NASA October 2024 shortlist; not an assigned landing site')}

def apply(settings,key):
    site=POLAR_SITES[key]
    for field in ('latitude','longitude','sun_elevation','sun_azimuth','camera_heading'):setattr(settings,field,site[field])
    settings.rock_coverage,settings.crater_density,settings.crater_depth=.179,.65,.8
    settings.micro_density,settings.micro_craters=8.,.35
    settings.camera_height,settings.camera_pitch,settings.camera_lens=1.8,-5.,32.
    settings.sun_energy,settings.sun_diameter,settings.visible_sun=3.8,.53,True

def location_from_json(document,known_ids):
    if not isinstance(document,dict) or document.get('schema')!='lunar-terrain-location-v1':raise ValueError('Choose a location JSON downloaded from the Lunar Atlas')
    key=document.get('preset')
    if not isinstance(key,str) or key not in known_ids:raise ValueError('Unknown location preset; update Lunar Terrain or choose a supported location')
    return key
