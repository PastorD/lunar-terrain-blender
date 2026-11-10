"""Camera-visible finite Sun, synchronized with the lighting Sun.
An angular world mask has no parallax. Camera rays only: no second illuminator.
"""
import bpy,math

def add(world,sun):
 n,l=world.node_tree.nodes,world.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputWorld');out.location=(800,0)
 bg=n.new('ShaderNodeBackground');bg.location=(580,0);bg.inputs['Color'].default_value=(1,1,1,1)
 geom=n.new('ShaderNodeNewGeometry');geom.location=(-900,200)
 direction=n.new('ShaderNodeCombineXYZ');direction.name='SUN_DIRECTION';direction.location=(-900,-160)
 expressions=['cos(rx)*sin(ry)*cos(rz)+sin(rx)*sin(rz)',
              'cos(rx)*sin(ry)*sin(rz)-sin(rx)*cos(rz)','cos(rx)*cos(ry)']
 for i,expr in enumerate(expressions):
  dr=direction.inputs[i].driver_add('default_value').driver;dr.expression=expr
  for name,axis in [('rx','ROT_X'),('ry','ROT_Y'),('rz','ROT_Z')]:
   v=dr.variables.new();v.name=name;v.type='TRANSFORMS';v.targets[0].id=sun
   v.targets[0].transform_type=axis;v.targets[0].transform_space='WORLD_SPACE'
 # Incoming points toward the observer; negate to obtain camera-to-world direction.
 rev=n.new('ShaderNodeVectorMath');rev.operation='SCALE';rev.inputs['Scale'].default_value=-1;rev.location=(-640,200)
 l.new(geom.outputs['Incoming'],rev.inputs[0])
 dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.location=(-410,100)
 l.new(rev.outputs['Vector'],dot.inputs[0]);l.new(direction.outputs[0],dot.inputs[1])
 edge=n.new('ShaderNodeMath');edge.operation='LESS_THAN';edge.location=(-170,100);edge.label='Angular solar radius'
 cross=n.new('ShaderNodeVectorMath');cross.operation='CROSS_PRODUCT';cross.location=(-410,370)
 l.new(rev.outputs['Vector'],cross.inputs[0]);l.new(direction.outputs[0],cross.inputs[1])
 length=n.new('ShaderNodeVectorMath');length.operation='LENGTH';length.location=(-170,370)
 l.new(cross.outputs['Vector'],length.inputs[0]);l.new(length.outputs['Value'],edge.inputs[0])
 front=n.new('ShaderNodeMath');front.operation='GREATER_THAN';front.inputs[1].default_value=0;front.location=(-170,550)
 l.new(dot.outputs['Value'],front.inputs[0])
 disc=n.new('ShaderNodeMath');disc.operation='MULTIPLY';disc.location=(70,370)
 l.new(front.outputs[0],disc.inputs[0]);l.new(edge.outputs[0],disc.inputs[1])
 dr=edge.inputs[1].driver_add('default_value').driver;dr.expression='sin(angle/2)'
 var=dr.variables.new();var.name='angle';var.type='SINGLE_PROP';var.targets[0].id_type='LIGHT';var.targets[0].id=sun.data;var.targets[0].data_path='angle'
 path=n.new('ShaderNodeLightPath');path.location=(-160,-150)
 mask=n.new('ShaderNodeMath');mask.operation='MULTIPLY';mask.location=(70,80)
 l.new(disc.outputs[0],mask.inputs[0]);l.new(path.outputs['Is Camera Ray'],mask.inputs[1])
 brightness=n.new('ShaderNodeMath');brightness.operation='MULTIPLY';brightness.location=(330,0)
 brightness.name='SOLAR_DISPLAY_RADIANCE';brightness.inputs[1].default_value=1000;brightness.label='Display radiance (not calibrated exposure)'
 l.new(mask.outputs[0],brightness.inputs[0]);l.new(brightness.outputs[0],bg.inputs['Strength']);l.new(bg.outputs[0],out.inputs[0])
 world.cycles.sampling_method='NONE'
 world['Sun_disc']='Camera-visible 0.53 degree angular mask. Follows actual light rotation and light angle. No atmospheric glow or extra world illumination.'
 return world
