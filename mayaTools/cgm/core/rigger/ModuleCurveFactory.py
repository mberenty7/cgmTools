"""
Module for building controls for cgmModules

"""
# From Python =============================================================
import copy
import re

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# From Maya =============================================================
import maya.cmds as mc

# From Red9 =============================================================
from Red9.core import Red9_Meta as r9Meta
from Red9.core import Red9_General as r9General

# From cgm ==============================================================
from cgm.core import cgm_Meta as cgmMeta
from cgm.core import cgm_PuppetMeta as cgmPM
from cgm.core.classes import SnapFactory as Snap
from cgm.core.lib import rayCaster as RayCast
from cgm.lib import (cgmMath,
                     locators,
                     modules,
                     distance,
                     dictionary,
                     rigging,
                     search,
                     curves,
                     lists,
                     )

from cgm.lib.classes import NameFactory
from cgm.core.lib import nameTools
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Modules
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 
class go(object):
    @r9General.Timer
    def __init__(self,moduleInstance,controlTypes = [],storageInstance = False,**kws): 
        """
	Class factor generating module controls
	
        @kws
	moduleInstance -- must be a module instance
        """
	self.d_controlBuildFunctions = {'cog':self.build_cog,
	                                'hips':self.build_hips,
	                                'segmentFK':self.build_segmentFKHandles,
	                                'segmentIK':self.build_segmentIKHandles}
        # Get our base info
        #==============	        
        #>>> module null data
        if not issubclass(type(moduleInstance),cgmPM.cgmModule):
            log.error("Not a cgmModule: '%s'"%moduleInstance)
            return 
	if not mc.objExists(moduleInstance.mNode):
	    raise StandardError,"RigFactory.go.init Module instance no longer exists: '%s'"%moduleInstance
	
	if type(controlTypes) is not list:controlTypes = [controlTypes]
        assert moduleInstance.isTemplated(),"Module is not templated: '%s'"%moduleInstance.getShortName()        
        assert moduleInstance.isSkeletonized(),"Module is not skeletonized: '%s'"%moduleInstance.getShortName()
        
        log.debug(">>> ModuleControlFactory.go.__init__")
        self._mi_module = moduleInstance# Link for shortness	
        """
        if moduleInstance.hasControls():
            if forceNew:
                deleteControls(moduleInstance)
            else:
                log.warning("'%s' has already been skeletonized"%moduleInstance.getShortName())
                return        
        """
        #>>> Gather info
        #=========================================================	
        self.l_moduleColors = self._mi_module.getModuleColors()
        self.l_coreNames = self._mi_module.coreNames.value
        self.mi_templateNull = self._mi_module.templateNull#speed link
	self.mi_rigNull = self._mi_module.rigNull#speed link
        self._targetMesh = self._mi_module.modulePuppet.getGeo() or 'Morphy_Body_GEO1'#>>>>>>>>>>>>>>>>>this needs better logic   
               
        #>>> part name 
        self._partName = self._mi_module.getPartNameBase()
        self._partType = self._mi_module.moduleType or False
	
        self._direction = None
        if self._mi_module.hasAttr('cgmDirection'):
            self._direction = self._mi_module.cgmDirection or None
               
        #>>> Instances and joint stuff
        self._jointOrientation = str(modules.returnSettingsData('jointOrientation')) or 'zyx'#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<   
	self.l_controlSnapObjects = []
	for mi_obj in self.mi_templateNull.controlObjects:
	    self.l_controlSnapObjects.append(mi_obj.helper.mNode)  
	self._skinOffset = 3 #Need to get from puppet!<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
	self.l_segmentControls = []
	self.l_segmentHandles = []
	self.l_indexPairs = lists.parseListToPairs(list(range(len(self.l_controlSnapObjects))))
	self.l_segments = lists.parseListToPairs(self.l_controlSnapObjects)		
	self.d_returnControls = {}	
	self.md_ReturnControls = {}	
        
        #>>> We need to figure out which control to make
	#===================================================================================
	self.l_controlsToMakeArg = []	
	
	if controlTypes:#If we get an override
	    for c in controlTypes:
		if self.validateControlArg(c):
		    self.l_controlsToMakeArg.append(c)
	else:
	    if not self._mi_module.getMessage('moduleParent'):
		self.l_controlsToMakeArg.append('cog')
	    #if self.mi_rigNull.ik:
		#self.l_controlsToMakeArg.extend(['vectorHandles'])
		#if self._partType == 'torso':#Maybe move to a dict?
		    #self.l_controlsToMakeArg.append('spineIKHandle')            
	    if self.mi_rigNull.fk:
		self.l_controlsToMakeArg.extend(['segmentFK','segmentIK'])
		if self._partType == 'torso':#Maybe move to a dict?
		    self.l_controlsToMakeArg.append('hips')
		    
	log.debug("l_controlsToMakeArg: %s"%self.l_controlsToMakeArg)
	    
	#self.d_controlShapes = mControlFactory.limbControlMaker(self.m,self.l_controlsToMakeArg)
	
	for key in self.l_controlsToMakeArg:
	    self.d_controlBuildFunctions[key]()#Run it
	    if key not in self.d_returnControls:
		log.warning("Necessary control shape(s) was not built: '%s'"%key)
		raise StandardError,"Did not get all necessary controls built"
	if storageInstance:
	    try:
		storageInstance._d_controlShapes = self.d_returnControls
		storageInstance._md_controlShapes = self.md_ReturnControls
	    except StandardError,error:
		log.error("storage fail! | %s"%storageInstance) 
		raise StandardError,"Did not get all necessary controls built"

    def validateControlArg(self,arg):
	"""returns function"""
	if arg in self.d_controlBuildFunctions.keys():
	    return True
	log.warning("validateControlArg couldn't find: %s"%arg)
	return False
    
    @r9General.Timer    
    def build_cog(self):
	try:
	    multiplier = 1.1
	    tmplRoot = self.mi_templateNull.root.mNode
	    mi_loc = cgmMeta.cgmNode(tmplRoot).doLoc()#make loc for sizing
	    mi_loc.doGroup()#group to zero
	    sizeReturn = returnBaseControlSize(mi_loc,self._targetMesh,axis=['x','y'])#Get size
	    l_size = [sizeReturn['x']+(self._skinOffset*2),sizeReturn['y']+(self._skinOffset*2)]
	    mc.delete(mi_loc.parent)#delete loc
	    
	    mi_crv = cgmMeta.cgmObject( curves.createControlCurve('circleArrow',direction = 'y+',size = max(l_size),absoluteSize=False))
	    Snap.go(mi_crv, tmplRoot) #Snap it
	    
	    #>>Copy tags and name
	    mi_crv.addAttr('cgmName',attrType='string',value = 'cog',lock=True)        
	    mi_crv.addAttr('cgmType',attrType='string',value = 'controlCurve',lock=True)
	    mi_crv.doName()        
    
	    #>>> Color
	    curves.setCurveColorByName(mi_crv.mNode,self.l_moduleColors[0])    
	    self.d_returnControls['cog'] = mi_crv.mNode
	    self.md_ReturnControls['cog'] = mi_crv
	except StandardError,error:
		log.error("build_cog fail! | %s"%error) 
		return False
	
    def build_hips(self):
	distanceMult = .5	    
	orientHelper = self.l_controlSnapObjects[1]
	log.debug(orientHelper)
	mi_loc = cgmMeta.cgmNode(orientHelper).doLoc()#make loc for sizing
	mi_loc.doGroup()#group to zero
	d_size = returnBaseControlSize(mi_loc,self._targetMesh,axis=['x','y','z-'])#Get size
	l_size = [d_size['x']+(self._skinOffset*2),d_size['y']+(self._skinOffset*2),d_size['z']+(self._skinOffset*2)]
	mi_crvShape = cgmMeta.cgmObject( curves.createControlCurve('semiSphere',direction = 'y-',size = 1))
	if len(self.l_controlSnapObjects)>2:#offset
	    distanceToMove = distance.returnDistanceBetweenObjects(orientHelper,self.l_controlSnapObjects[1])
	    mi_loc.tz = -(distanceToMove*distanceMult)#Offset it	
	    
	#mc.makeIdentity(mi_crv.mNode,apply=True, scale=True)
	Snap.go(mi_crvShape.mNode, mi_loc.mNode)#Snap it
	
	mi_crv = cgmMeta.cgmObject( rigging.groupMeObject(mi_loc.mNode,False) )	
	mc.delete(mi_loc.parent)#delete loc
	
	curves.parentShapeInPlace(mi_crv.mNode,mi_crvShape.mNode)#Parent shape
	
	#mc.delete(mi_crv.mNode)
	mi_crvShape.delete()	    
	mc.scale(l_size[0],l_size[1],l_size[2],mi_crv.mNode,os = True, relative = True)
	#mi_crv.sy = d_size['z']
	
	#pBuffer = mi_crv.parent
	#mi_crv.parent = False
	#mc.delete(pBuffer)
	
	#>>Copy tags and name
	mi_crv.addAttr('cgmName',attrType='string',value = 'hips',lock=True)        
	mi_crv.addAttr('cgmType',attrType='string',value = 'controlCurve',lock=True)
	mi_crv.doName()        
	
	#>>> Color
	curves.setCurveColorByName(mi_crv.mNode,self.l_moduleColors[0])    
	self.d_returnControls['hips'] = mi_crv.mNode
	self.md_ReturnControls['hips'] = mi_crv
	    	    
	"""except StandardError,error:
		log.error("build_hips fail! | %s"%error) 
		return False"""
    	    
    @r9General.Timer    
    def build_segmentFKHandles(self):
	try:
	    l_segmentControls = []
	    l_iSegmentControls = []
	    if self._partType == 'torso':
		l_segmentsToDo = self.l_segments[1:]
	    else:
		l_segmentsToDo = self.l_segments
		
	    for i,seg in enumerate(l_segmentsToDo):
		returnBuffer = createWrapControlShape(seg,self._targetMesh,
		                                      points = 10,
		                                      curveDegree=1,
		                                      insetMult = .2,
		                                      posOffset = [0,0,self._skinOffset*.75],
		                                      joinMode=True,
		                                      extendMode='segment')
		mi_crv = returnBuffer['instance']	    
		#>>> Color
		curves.setCurveColorByName(mi_crv.mNode,self.l_moduleColors[0])                    
		mi_crv.addAttr('cgmType',attrType='string',value = 'segFKCurve',lock=True)	
		mi_crv.doName()
		
		#Store for return
		l_segmentControls.append( mi_crv.mNode )
		l_iSegmentControls.append( mi_crv )
		
	    self.d_returnControls['segmentFK'] = l_segmentControls 
	    self.md_ReturnControls['segmentFK'] = l_iSegmentControls
	    
	except StandardError,error:
		log.error("build_segmentIKHandles fail! | %s"%error) 
		return False
	    
    @r9General.Timer	
    def build_segmentIKHandles(self):
	try:
	    l_segmentControls = []
	    l_iSegmentControls = []
	    
	    if self._partType == 'torso':
		l_segmentsToDo = self.l_segments[1:]
	    else:
		l_segmentsToDo = self.l_segments

	    for i,seg in enumerate(l_segmentsToDo):
		returnBuffer = createWrapControlShape(seg,self._targetMesh,
		                                      points = 8,
		                                      curveDegree=3,
		                                      insetMult = .2,
		                                      posOffset = [0,0,self._skinOffset*1.8],
		                                      joinMode=True,
		                                      extendMode='radial')
		mi_crv = returnBuffer['instance']	    
		#>>> Color
		curves.setCurveColorByName(mi_crv.mNode,self.l_moduleColors[1])                    
		mi_crv.addAttr('cgmType',attrType='string',value = 'segIKCurve',lock=True)	
		mi_crv.doName()
		
		#Store for return
		l_segmentControls.append( mi_crv.mNode )
		l_iSegmentControls.append( mi_crv )
		
	    self.d_returnControls['segmentIK'] = l_segmentControls 
	    self.md_ReturnControls['segmentIK'] = l_iSegmentControls
	    
	    if len(self.l_segments)>2:
		objects = self.l_controlSnapObjects[-2:]
	    else:
		objects = self.l_segments[-1]
	    returnBuffer = createWrapControlShape(self.l_segments[-1],self._targetMesh,
	                                          points = 8,
	                                          curveDegree=3,
	                                          posOffset = [0,0,self._skinOffset],
	                                          joinMode=True,
	                                          extendMode='segment')
	    mi_crv = returnBuffer['instance']	    
	    #>>> Color
	    curves.setCurveColorByName(mi_crv.mNode,self.l_moduleColors[0])                    
	    mi_crv.doCopyNameTagsFromObject(self.l_controlSnapObjects[-1],ignore = ['cgmType'])
	    mi_crv.addAttr('cgmType',attrType='string',value = 'ikCurve',lock=True)	    
	    mi_crv.doName()
		
	    self.d_returnControls['segmentIKEnd'] = mi_crv.mNode 		
	    self.md_ReturnControls['segmentIKEnd'] = mi_crv
		
	except StandardError,error:
		log.error("build_segmentIKHandles! | %s"%error) 
		return False
	    
def returnBaseControlSize(mi_obj,mesh,axis=True):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Figure out the base size for a control from a point in space within a mesh

    ARGUMENTS:
    mi_obj(cgmObject instance)
    mesh(obj) = ['option1','option2']
    axis(list) -- what axis to check
    
    RETURNS:
    axisDistances(list)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """ 
    #if type(l_mesh) not in [list,tuple]:l_mesh = [l_mesh]
    if mc.objExists(mi_obj):
	try:
	    mi_obj = cgmMeta.cgmObject(mi_obj)
	except StandardError,error:
		log.error("returnBaseControlSize Failed to initialize mi_obj! | %s"%error) 
		raise StandardError    
    elif not issubclass(type(mi_obj),cgmMeta.cgmObject):
	try:
	    mi_obj = cgmMeta.cgmObject(mi_obj.mNode)
	except StandardError,error:
		log.error("returnBaseControlSize Failed to initialize existing instance as mi_obj! | %s"%error) 
		raise StandardError  
	    
   	   
    #>>>Figure out the axis to do
    d_axisToDo = {}
    if axis == True:
        axis = ['x','y','z']
    if type(axis) in [list,tuple]:
        for a in axis:
            if a in dictionary.stringToVectorDict.keys():
                if list(a)[0] in d_axisToDo.keys():
                    d_axisToDo[list(a)[0]].append( a )
                else:
                    d_axisToDo[list(a)[0]] = [ a ]
                     
            elif type(a) is str and a.lower() in ['x','y','z']:
                buffer = []
                buffer.append('%s+'%a.lower())
                buffer.append('%s-'%a.lower())  
                d_axisToDo[a.lower()] = buffer
            else:
                log.warning("Don't know what with: '%s'"%a)
    
    log.debug(d_axisToDo)
    if not d_axisToDo:return False
    #>>>
    d_returnDistances = {}
    for axis in d_axisToDo:
        log.debug("Checking: %s"%axis)
        directions = d_axisToDo[axis]
        if len(directions) == 1:#gonna multiply our distance 
            info = RayCast.findMeshIntersectionFromObjectAxis(mesh,mi_obj.mNode,directions[0])
            d_returnDistances[axis] = (distance.returnDistanceBetweenPoints(info['hit'],mi_obj.getPosition()) *2)
        else:
            info1 = RayCast.findMeshIntersectionFromObjectAxis(mesh,mi_obj.mNode,directions[0])
            info2 = RayCast.findMeshIntersectionFromObjectAxis(mesh,mi_obj.mNode,directions[1])
            if info1 and info2:
                d_returnDistances[axis] = distance.returnDistanceBetweenPoints(info1['hit'],info2['hit'])                    
    log.debug(d_returnDistances) 
    return d_returnDistances

  
@r9General.Timer    
def createWrapControlShape(targetObjects,
                           targetGeo = None,
                           latheAxis = 'z',aimAxis = 'y+',
                           points = 8,
                           curveDegree = 1,
                           insetMult = None,#Inset multiplier
                           posOffset = [],
                           joinMode = False,
                           extendMode = None):#'segment,radial' 
    """
    Function for creating control curves from other objects. Currently assumes z aim, y up
    1) Cather info
    2) Get initial curves
    3) Store info
    4) return
    """  
    if type(targetObjects) not in [list,tuple]:targetObjects = [targetObjects]
    if not targetGeo:
	raise NotImplementedError, "Must have geo for now"
    assert type(points) is int,"Points must be int: %s"%points
    assert type(curveDegree) is int,"Points must be int: %s"%points
    assert curveDegree > 0,"Curve degree must be greater than 1: %s"%curveDegree
    
    log.debug("targetObjects: %s"%targetObjects)
    
    #>>> Info
    l_groupsBuffer = []
    il_curvesToCombine = []
    l_sliceReturns = []
    #Need to do more to get a better size
    
    #>>> Build curves
    #=================================================================
    #> Root curve #
    mi_rootLoc = cgmMeta.cgmNode(targetObjects[0]).doLoc()
    #>>> Root
    mi_rootLoc.doGroup()#Group to zero    
    if extendMode == 'segment':
	if len(targetObjects) < 2:
	    log.warning("Segment build mode only works with two objects or more")    
	else:
	    if insetMult is not None:
		rootDistanceToMove = distance.returnDistanceBetweenObjects(targetObjects[0],targetObjects[1])
		log.debug("rootDistanceToMove: %s"%rootDistanceToMove)
		mi_rootLoc.tz = (rootDistanceToMove*insetMult)#Offset it
	    
	    for i,obj in enumerate(targetObjects[1:]):
		log.debug(i)
		log.debug(len(targetObjects[1:]))
		#> End Curve
		mi_endLoc = cgmMeta.cgmNode(obj).doLoc()
		mi_endLoc.doGroup()
		if i == len(targetObjects[1:])-1:
		    if insetMult is not None:
			distanceToMove = distance.returnDistanceBetweenObjects(targetObjects[-1],targetObjects[0])
			log.debug("distanceToMove: %s"%distanceToMove)
			mi_endLoc.tz = -(distanceToMove*insetMult)#Offset it  
		d_endCastInfo = createMeshSliceCurve(targetGeo,mi_endLoc,curveDegree=curveDegree,latheAxis=latheAxis,aimAxis=aimAxis,posOffset = posOffset,points = points,returnDict=True) 
		l_sliceReturns.append(d_endCastInfo)
		mi_end = cgmMeta.cgmObject(d_endCastInfo['curve'])
		il_curvesToCombine.append(mi_end)
		mc.delete(mi_endLoc.parent)#delete the loc
	    
    elif extendMode == 'radial':
	d_handleOuterInfo = createMeshSliceCurve(targetGeo,mi_rootLoc,curveDegree=curveDegree,latheAxis=latheAxis,aimAxis=aimAxis,posOffset = 0,points = points,returnDict=True) 
	mi_buffer = cgmMeta.cgmObject(d_handleOuterInfo['curve'])#instance curve	
	l_sliceReturns.append(d_handleOuterInfo)
	il_curvesToCombine.append(mi_buffer)    
	
    #Now cast our root since we needed to move it with segment mode before casting 
    d_rootCastInfo = createMeshSliceCurve(targetGeo,mi_rootLoc,curveDegree=curveDegree,latheAxis=latheAxis,aimAxis=aimAxis,posOffset = posOffset,points = points,returnDict=True)  
    l_sliceReturns.insert(0,d_rootCastInfo)
    mi_root = cgmMeta.cgmObject(d_rootCastInfo['curve'])#instance curve
    il_curvesToCombine.append(mi_root)    
    
    mc.delete(mi_rootLoc.parent)#delete the loc
    
    l_curvesToCombine = [mi_obj.mNode for mi_obj in il_curvesToCombine]#Build our combine list before adding connectors         
    
    if joinMode and len(l_sliceReturns)>1:
	#> Side Curves
	for degree in d_rootCastInfo['processedHits'].keys():
	    l_pos = []	    
	    for d in l_sliceReturns:
		l_pos.append( d['processedHits'].get(degree) or False )
	    if False in l_pos:
		l_pos.remove(False)
	    log.debug("l_pos: %s"%l_pos)
	    if len(l_pos)>=2:
		l_curvesToCombine.append( mc.curve(d=curveDegree,ep=l_pos,os =True) )#Make the curve
		
    #>>>Combine the curves
    newCurve = curves.combineCurves(l_curvesToCombine) 
    mi_crv = cgmMeta.cgmObject( rigging.groupMeObject(targetObjects[0],False) )
    curves.parentShapeInPlace(mi_crv.mNode,newCurve)#Parent shape
    mc.delete(newCurve)
    
    #>>Copy tags and name
    mi_crv.doCopyNameTagsFromObject(targetObjects[0],ignore = ['cgmType'])
    mi_crv.addAttr('cgmType',attrType='string',value = 'controlCurve')
    mi_crv.doName()                
        
    #Store for return
    return {'curve':mi_crv.mNode,'instance':mi_crv}  
 
#@r9General.Timer
def createMeshSliceCurve(mesh, mi_obj,latheAxis = 'z',aimAxis = 'y+',
                         points = 12, curveDegree = 3,
                         posOffset = 0, markHits = False,
                         initialRotate = 0,offsetMode = 'vector',
                         returnDict = False):
    """
    This function lathes an axis of an object, shoot rays out the aim axis at the provided mesh and returning hits. 
    it then uses this information to build a curve shape.
    
    @Paremeters
    mi_obj(string instance) -- object to use as base
    latheAxis(str) -- axis of the objec to lathe TODO: add validation
    aimAxis(str) -- axis to shoot out of
    points(int) -- how many points you want in the curve
    posOffset(vector) -- transformational offset for the hit from a normalized locator at the hit. Oriented to the surface
    markHits(bool) -- whether to keep the hit markers
    returnDict(bool) -- whether you want all the infomation from the process.
    """
    if issubclass(type(mi_obj),cgmMeta.cgmObject):
        mi_obj = mi_obj
    else:
        try:
	    mi_obj = cgmMeta.cgmObject(mi_obj)
	except StandardError,error:
		log.error(error) 
		return False
    log.debug("Casting: '%s"%mi_obj.mNode)
    if type(mesh) in [list,tuple]:
	log.error("Can only pass one mesh. passing first: '%s'"%mesh[0])
	mesh = mesh[0]
    assert mc.objExists(mesh),"Mesh doesn't exist: '%s'"%mesh
    mi_loc = mi_obj.doLoc()
    mi_loc.doGroup()
    l_pos = []
    d_returnDict = {}
    d_hitReturnFromValue = {}
    d_processedHitFromValue = {}
    rotateBaseValue = 360/points
    for i in range(points):
	d_castReturn = {}
	hit = False
	rotateValue = (rotateBaseValue*i) + initialRotate
	#shoot our ray, store the hit
	log.debug("Casting: %i>>%f"%(i,rotateValue))
	mi_loc.__setattr__('rotate%s'%latheAxis.capitalize(),rotateValue)	
	try:
	    d_castReturn = RayCast.findMeshIntersectionFromObjectAxis(mesh, mi_loc.mNode, axis=aimAxis)
	    d_hitReturnFromValue[rotateValue] = d_castReturn	    
	    try:hit = d_castReturn.get('hit')
	    except:hit = False	
	except StandardError,error:
		log.error(error) 
	if hit:
	    if markHits or posOffset:
		mi_tmpLoc = cgmMeta.cgmObject(mc.spaceLocator()[0])
		mc.move (hit[0],hit[1],hit[2], mi_tmpLoc.mNode)	
		if posOffset:
		    if offsetMode =='vector':
			constBuffer = mc.aimConstraint(mi_obj.mNode,mi_tmpLoc.mNode,
			                                  aimVector=[0,0,-1],
			                                  upVector=[0,1,0],
			                                  worldUpType = 'scene')
		    else:
			constBuffer = mc.normalConstraint(mesh,mi_tmpLoc.mNode,
			                                  aimVector=[0,0,1],
			                                  upVector=[0,1,0],
			                                  worldUpType = 'scene')
		    mc.delete(constBuffer)
		    mc.move(posOffset[0],posOffset[1],posOffset[2], [mi_tmpLoc.mNode], r=True, rpr = True, os = True, wd = True)
		    hit = mi_tmpLoc.getPosition()
		if not markHits:
		    mi_tmpLoc.delete()
		
	    l_pos.append(hit)
	    d_processedHitFromValue[rotateValue] = hit
		
    mc.delete(mi_loc.parent)
    if len(l_pos)>3:
	buffer = l_pos[0]
	l_finalPos = l_pos.append(buffer)
	curveBuffer =  mc.curve (d=curveDegree, ep = l_pos, os=True)
	if returnDict:
	    return {'curve':curveBuffer,
	            'processedHits':d_processedHitFromValue,
	            'hitReturns':d_hitReturnFromValue}
	else:
	    return curveBuffer
    
    return False    

'''	
@r9General.Timer
def limbControlMaker(moduleInstance,controlTypes = ['cog']):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    * Save the new positional information from the template objects
    * Collect all names of objects for a delete list
    * If anything in the module doesn't belong there, un parent it, report it
        * like a template object parented to another obect

    ARGUMENTS:
    moduleNull(string)
    controlTypes(list) = ['option1','option2']
    
    RETURNS:
    limbJoints(list)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """ 
    if type(controlTypes) is not list:controlTypes = [controlTypes]
    if not issubclass(type(moduleInstance),cgmPM.cgmModule):
        log.error("Not a cgmModule: '%s'"%moduleInstance)
        return 
    
    assert moduleInstance.mClass in ['cgmModule','cgmLimb'],"Not a module"
    assert moduleInstance.isTemplated(),"Module is not templated: '%s'"%moduleInstance.getShortName()        
    assert moduleInstance.isSkeletonized(),"Module is not skeletonized: '%s'"%moduleInstance.getShortName()
    
    log.info(">>> ModuleControlFactory.go.__init__")
    mi_m = moduleInstance# Link for shortness    
    """
    if moduleInstance.hasControls():
        if forceNew:
            deleteControls(moduleInstance)
        else:
            log.warning("'%s' has already been skeletonized"%moduleInstance.getShortName())
            return        
    """
    #>>> Gather info
    #=========================================================
    l_moduleColors = mi_m.getModuleColors()
    l_coreNames = mi_m.coreNames.value
            
    #>>> part name 
    partName = mi_m.getPartNameBase()
    partType = mi_m.moduleType or False
    
    direction = None
    if mi_m.hasAttr('cgmDirection'):
        direction = mi_m.cgmDirection or None
        
    
    #Gether information 
    mi_templateNull = mi_m.templateNull
    bodyGeo = mi_m.modulePuppet.getGeo() or ['Morphy_Body_GEO1'] #>>>>>>>>>>>>>>>>>this needs better logic
    l_controlSnapObjects = []
    for mi_obj in mi_templateNull.controlObjects:
        l_controlSnapObjects.append(mi_obj.helper.mNode)  
    skinDepth = 2.5
    d_returnControls = {}
    if 'fkSegmentControls' in controlTypes:
	    l_segmentControls = []
	    l_segmentHandles = []
	    l_indexPairs = lists.parseListToPairs(list(range(len(l_controlSnapObjects))))
	    l_segments = lists.parseListToPairs(l_controlSnapObjects)
	    for i,seg in enumerate(l_segments):
		#> Figure out a base scale and set it
		if not bodyGeo:
		    raise StandardError,"NO BODY GEO"
		
		log.debug("segment: %s"%seg)
		log.debug("indices: %s"%l_indexPairs[i])
		distanceMult = .2
		
		#>>> Get a base distance
		distanceToMove = distance.returnDistanceBetweenObjects(seg[0],seg[1])
		log.debug("distanceToMove: %s"%distanceToMove)
		l_groupsBuffer = []
		#Need to do more to get a better size
		
		#>>> Build curves
		#=================================================================
		points = 8
		curveDegree = 1
		posOffset = [0,0,skinDepth*1.25]
		#> Root curve #
		mi_rootLoc = cgmMeta.cgmNode(seg[0]).doLoc()
			    
		#>>> Root
		mi_rootLoc.doGroup()
		mi_rootLoc.tz = (distanceToMove*distanceMult)#Offset it
		
		d_rootCastInfo = createMeshSliceCurve(bodyGeo[0],mi_rootLoc,curveDegree=curveDegree,posOffset = posOffset,points = points,returnDict=True) 
		mi_root = cgmMeta.cgmObject(d_rootCastInfo['curve'])
		    
		#> End Curve
		mi_endLoc = cgmMeta.cgmNode(seg[1]).doLoc()
		mi_endLoc.doGroup()
		mi_endLoc.tz = -(distanceToMove*distanceMult)#Offset it  
		d_endCastInfo = createMeshSliceCurve(bodyGeo[0],mi_endLoc,curveDegree=curveDegree,posOffset = posOffset,points = points,returnDict=True) 
		mi_end = cgmMeta.cgmObject(d_endCastInfo['curve'])          
		
		#> Side Curves
		l_rootPos = []
		l_endPos = []
		l_curvesToCombine = []
		for degree in d_rootCastInfo['processedHits'].keys():
		    rootPoint = d_rootCastInfo['processedHits'].get(degree) or False
		    endPoint = d_endCastInfo['processedHits'].get(degree) or False
		    if rootPoint and endPoint:
			l_curvesToCombine.append( mc.curve(d=1,ep=[rootPoint,endPoint],os =True) )#Make the curve
		    else:
			log.warning("Failed to find side data on: %s"%(seg))
    
		#>>>Store groups
		l_groupsBuffer.append( mi_endLoc.parent )
		l_groupsBuffer.append( mi_rootLoc.parent )
    
		#>>>Combine the curves
		l_curvesToCombine.extend([mi_root.mNode,mi_end.mNode])            
		newCurve = curves.combineCurves(l_curvesToCombine) 
		mi_crv = cgmMeta.cgmObject( rigging.groupMeObject(seg[0],False) )
		curves.parentShapeInPlace(mi_crv.mNode,newCurve)#Parent shape
		mc.delete(newCurve)
		
		#>>Copy tags and name
		mi_crv.doCopyNameTagsFromObject(seg[0],ignore = ['cgmType'])
		mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
		mi_crv.addAttr('cgmTypeModifier',attrType='string',value = 'fk')				
		mi_crv.doName()
		
		#>>> Color
		curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])                    
		
		#>>>Clean up groups
		for g in l_groupsBuffer:
		    if mc.objExists(g):
			mc.delete(g)
		
		#Store for return
		l_segmentControls.append( mi_crv.mNode )
	    d_returnControls['fkSegmentControls'] = l_segmentControls 
	    
    if 'ikSegmentControls' in controlTypes:
	    l_segmentControls = []
	    l_segmentHandles = []
	    distanceMult = .025	  
	    points = 8
	    curveDegree = 3
	    posOffset = [0,0,skinDepth]	    
	    l_indexPairs = lists.parseListToPairs(list(range(len(l_controlSnapObjects))))
	    l_segments = lists.parseListToPairs(l_controlSnapObjects)
	    for i,seg in enumerate(l_segments):
		#> Figure out a base scale and set it
		if not bodyGeo:
		    raise StandardError,"NO BODY GEO"
		
		log.debug("segment: %s"%seg)
		log.debug("indices: %s"%l_indexPairs[i])
		
		#>>> Get a base distance
		distanceToMove = distance.returnDistanceBetweenObjects(seg[0],seg[1])
		log.debug("distanceToMove: %s"%distanceToMove)
		l_groupsBuffer = []
		#Need to do more to get a better size
		
		#>>> Build curves
		#=================================================================
		#> Root curve #
		mi_rootLoc = cgmMeta.cgmNode(seg[0]).doLoc()
			    
		#>>> Root
		mi_rootLoc.doGroup()
		mi_rootLoc.tz = (distanceToMove*distanceMult)#Offset it
		
		d_rootCastInfo = createMeshSliceCurve(bodyGeo[0],mi_rootLoc,curveDegree=curveDegree,posOffset = posOffset,points = points,returnDict=True) 
		mi_root = cgmMeta.cgmObject(d_rootCastInfo['curve'])
		    
		#> End Curve
		mi_rootLoc.tz = -(distanceToMove*distanceMult)#Offset it  
		d_endCastInfo = createMeshSliceCurve(bodyGeo[0],mi_rootLoc,curveDegree=curveDegree,posOffset = posOffset,points = points,returnDict=True) 
		mi_end = cgmMeta.cgmObject(d_endCastInfo['curve'])          
		
		#> Side Curves
		l_rootPos = []
		l_endPos = []
		l_curvesToCombine = []
		for degree in d_rootCastInfo['processedHits'].keys():
		    rootPoint = d_rootCastInfo['processedHits'].get(degree) or False
		    endPoint = d_endCastInfo['processedHits'].get(degree) or False
		    if rootPoint and endPoint:
			l_curvesToCombine.append( mc.curve(d=1,ep=[rootPoint,endPoint],os =True) )#Make the curve
		    else:
			log.warning("Failed to find side data on: %s"%(seg))
    
		#>>>Store groups
		l_groupsBuffer.append( mi_rootLoc.parent )
    
		#>>>Combine the curves
		l_curvesToCombine.extend([mi_root.mNode,mi_end.mNode])            
		newCurve = curves.combineCurves(l_curvesToCombine) 
		mi_crv = cgmMeta.cgmObject( rigging.groupMeObject(seg[0],False) )
		curves.parentShapeInPlace(mi_crv.mNode,newCurve)#Parent shape
		mc.delete(newCurve)
		
		#>>Copy tags and name
		mi_crv.doCopyNameTagsFromObject(seg[0],ignore = ['cgmType'])
		mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
		mi_crv.addAttr('cgmTypeModifier',attrType='string',value = 'ik')		
		mi_crv.doName()
		
		#>>> Color
		curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])                    
		
		#>>>Clean up groups
		for g in l_groupsBuffer:
		    if mc.objExists(g):
			mc.delete(g)
		
		#Store for return
		l_segmentControls.append( mi_crv.mNode )
	    d_returnControls['ikSegmentControls'] = l_segmentControls 
	    
    if 'segmentControlsNEW' in controlTypes:
        l_segmentControls = []
	l_segmentHandles = []
        l_indexPairs = lists.parseListToPairs(list(range(len(l_controlSnapObjects))))
        l_segments = lists.parseListToPairs(l_controlSnapObjects)
        for i,seg in enumerate(l_segments):
            #> Figure out a base scale and set it
            if not bodyGeo:
                raise StandardError,"NO BODY GEO"
	    
            log.debug("segment: %s"%seg)
            log.debug("indices: %s"%l_indexPairs[i])
	    distanceMult = .2
	    
            #>>> Get a base distance
            distanceToMove = distance.returnDistanceBetweenObjects(seg[0],seg[1])
            log.debug("distanceToMove: %s"%distanceToMove)
            l_groupsBuffer = []
            #Need to do more to get a better size
            
            #>>> Build curves
            #=================================================================
	    points = 8
            #> Root curve #
            mi_rootLoc = cgmMeta.cgmNode(seg[0]).doLoc()
	    
	    #>>> Handle
	    d_handleInnerInfo = createMeshSliceCurve(bodyGeo[0],mi_rootLoc,posOffset = [0,0,skinDepth],points = points,returnDict=True) 
	    d_handleOuterInfo = createMeshSliceCurve(bodyGeo[0],mi_rootLoc,posOffset = [0,0,skinDepth*2],points = points,returnDict=True) 
            l_handleCurvesToCombine = [d_handleInnerInfo['curve'],d_handleOuterInfo['curve']]    
	    
            mi_handle = cgmMeta.cgmObject( rigging.groupMeObject(seg[0],False) )
	    
	    for degree in [0,90,180,270]:
		rootPoint = d_handleInnerInfo['processedHits'].get(degree) or False
		endPoint = d_handleOuterInfo['processedHits'].get(degree) or False
		if rootPoint and endPoint:
		    l_handleCurvesToCombine.append( mc.curve(d=1,ep=[rootPoint,endPoint],os =True) )#Make the curve
		else:
		    log.warning("Failed to find side data on: %s"%(seg))
	    
	    newCurve = curves.combineCurves(l_handleCurvesToCombine)   
            curves.parentShapeInPlace(mi_handle.mNode,newCurve)#Parent shape
	    mc.delete(newCurve)
            
	    
            #>>Copy tags and name
            mi_handle.doCopyNameTagsFromObject(seg[0],ignore = ['cgmType'])
            mi_handle.addAttr('cgmType',attrType='string',value = 'controlAnim')
            mi_handle.addAttr('cgmTypeModifier',attrType='string',value = 'handle')	    
            mi_handle.doName()
            
            #>>> Color
            curves.setCurveColorByName(mi_handle.mNode,l_moduleColors[1]) 	    
	    
	    #>>> Main Curve =====================================================
	    #>>> Root
            mi_rootLoc.doGroup()
            mi_rootLoc.tz = (distanceToMove*distanceMult)#Offset it
            
	    d_rootCastInfo = createMeshSliceCurve(bodyGeo[0],mi_rootLoc,posOffset = [0,0,skinDepth],points = points,returnDict=True) 
            mi_root = cgmMeta.cgmObject(d_rootCastInfo['curve'])
	        
            #> End Curve
            mi_endLoc = cgmMeta.cgmNode(seg[1]).doLoc()
            mi_endLoc.doGroup()
            mi_endLoc.tz = -(distanceToMove*distanceMult)#Offset it  
	    d_endCastInfo = createMeshSliceCurve(bodyGeo[0],mi_endLoc,posOffset = [0,0,skinDepth],points = points,returnDict=True) 
            mi_end = cgmMeta.cgmObject(d_endCastInfo['curve'])          
            
            #> Side Curves
            l_rootPos = []
            l_endPos = []
            l_curvesToCombine = []
	    for degree in [0,90,180,270]:
		rootPoint = d_rootCastInfo['processedHits'].get(degree) or False
		endPoint = d_endCastInfo['processedHits'].get(degree) or False
		if rootPoint and endPoint:
		    l_curvesToCombine.append( mc.curve(d=1,ep=[rootPoint,endPoint],os =True) )#Make the curve
		else:
		    log.warning("Failed to find side data on: %s"%(seg))

            #>>>Store groups
            l_groupsBuffer.append( mi_endLoc.parent )
            l_groupsBuffer.append( mi_rootLoc.parent )

            #>>>Combine the curves
            l_curvesToCombine.extend([mi_root.mNode,mi_end.mNode])            
            newCurve = curves.combineCurves(l_curvesToCombine) 
            mi_crv = cgmMeta.cgmObject( rigging.groupMeObject(seg[0],False) )
            curves.parentShapeInPlace(mi_crv.mNode,newCurve)#Parent shape
            mc.delete(newCurve)
            
            #>>Copy tags and name
            mi_crv.doCopyNameTagsFromObject(seg[0],ignore = ['cgmType'])
            mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
            mi_crv.doName()
            
            #>>> Color
            curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])                    
            
            #>>>Clean up groups
            for g in l_groupsBuffer:
                if mc.objExists(g):
                    mc.delete(g)
            
            #Store for return
            l_segmentControls.append( mi_crv.mNode )
	    l_segmentHandles.append( mi_handle.mNode )
        d_returnControls['segmentControls'] = l_segmentControls 
        d_returnControls['segmentHandles'] = l_segmentHandles 
            
    if 'segmentControls2' in controlTypes:
            l_segmentControls = []
            l_indexPairs = lists.parseListToPairs(list(range(len(l_controlSnapObjects))))
            l_segments = lists.parseListToPairs(l_controlSnapObjects)
            for i,seg in enumerate(l_segments):
                log.debug("segment: %s"%seg)
                log.debug("indices: %s"%l_indexPairs[i])
                mi_loc = cgmMeta.cgmObject(mc.spaceLocator()[0])#Make a loc            
                #>>> Get a base distance
                distanceToMove = distance.returnDistanceBetweenObjects(seg[0],seg[1])
                log.debug("distanceToMove: %s"%distanceToMove)
                l_groupsBuffer = []
                #Need to do more to get a better size
                
                #>>> Build curves
                #=================================================================
                #> Root curve #
                mi_root = cgmMeta.cgmObject(curves.createControlCurve('circle',1))
                Snap.go(mi_root.mNode,seg[0],move = True, orient = True)#Snap it
                mi_root.doGroup()
                mi_root.tz = (distanceToMove*.1)#Offset it
                
                #> End Curve
                mi_end = cgmMeta.cgmObject(curves.createControlCurve('circle',1))
                Snap.go(mi_end.mNode,seg[1],move = True, orient = True)#Snap it
                mi_end.doGroup()
                mi_end.tz = -(distanceToMove*.1)#Offset it  
                
                #> Figure out a base scale and set it
                if bodyGeo:
                    multiplier = 1.25
                    log.debug("Shrinkwrap mode")
                    Snap.go(mi_loc.mNode,mi_root.parent,move = True, orient = True)#Snap
                    mi_loc.parent = mi_root.parent#parent

                    d_info = returnBaseControlSize(mi_loc,bodyGeo[0],axis = ['x','y'])
                    xScale = d_info['x']
                    yScale = d_info['y']
                    log.debug("x: %s"%xScale)
                    log.debug("y: %s"%yScale)                
                    #> Now our first pass of scaling
                    mi_root.sx = xScale*1.25
                    mi_root.sy = yScale*1.25
                    mi_root.sz = 1
                    
                    mi_end.sx = xScale*1.25
                    mi_end.sy = yScale*1.25
                    mi_end.sz = 1    
                    #> Now we're gonna strink wrap it
                    for mi_crv in [mi_root,mi_end]:
                        Snap.go(mi_crv ,targets = bodyGeo[0],orient = False,snapToSurface=True,snapComponents=True,posOffset=[0,0,skinDepth])                    
                        log.debug(mi_crv.getShortName())
    
                #> Side Curves
                l_rootPos = []
                l_endPos = []
                l_curvesToCombine = []
                for cv in [0,3,5,7]:
                    l_posBuffer = []
                    #>>> Need to get u positions for more accuracy
                    l_posBuffer.append(cgmMeta.cgmNode('%s.ep[%i]'%(mi_root.mNode,cv-1)).getPosition())
                    l_posBuffer.append(cgmMeta.cgmNode('%s.ep[%i]'%(mi_end.mNode,cv-1)).getPosition())
                    l_curvesToCombine.append( mc.curve(d=1,p=l_posBuffer,os =True) )#Make the curve
                
                #>>>Store groups
                l_groupsBuffer.append( mi_end.parent )
                l_groupsBuffer.append( mi_root.parent )
    
                #>>>Combine the curves
                l_curvesToCombine.extend([mi_root.mNode,mi_end.mNode])            
                newCurve = curves.combineCurves(l_curvesToCombine) 
                mi_crv = cgmMeta.cgmObject( rigging.groupMeObject(seg[0],False) )
                curves.parentShapeInPlace(mi_crv.mNode,newCurve)#Parent shape
                mc.delete(newCurve)
                
                #>>Copy tags and name
                mi_crv.doCopyNameTagsFromObject(seg[0],ignore = ['cgmType'])
                mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
                mi_crv.doName()
                
                #>>> Color
                curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])                    
                
                #>>>Clean up groups
                for g in l_groupsBuffer:
                    if mc.objExists(g):
                        mc.delete(g)
                
                #Store for return
                l_segmentControls.append( mi_crv.mNode )
    
            d_returnControls['segmentControls'] = l_segmentControls 
	    
    if 'cog' in controlTypes:
        if 'segmentControls' not in d_returnControls.keys():
            log.warn("Don't have cog creation without segment controls at present")
            return False
        
        mi_crv = cgmMeta.cgmObject( curves.createControlCurve('circleArrow',direction = 'y+',absoluteSize=False))
        Snap.go(mi_crv, d_returnControls['segmentControls'][0]) #Snap it
        size = distance.returnBoundingBoxSize(d_returnControls['segmentControls'][0],True)#Get size
        log.debug(size)
        mc.scale(size[0]*1.1,size[1],size[2]*1.1,mi_crv.mNode,relative = True)
        
        #>>Copy tags and name
        mi_crv.addAttr('cgmName',attrType='string',value = 'cog')        
        mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
        mi_crv.doName()        

        #>>> Color
        curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])    
        
        d_returnControls['cog'] = mi_crv.mNode
	
    if 'cog2' in controlTypes:
        if 'segmentControls' not in d_returnControls.keys():
            log.warn("Don't have cog creation without segment controls at present")
            return False
        
        mi_crv = cgmMeta.cgmObject( curves.createControlCurve('cube',1))
        Snap.go(mi_crv, d_returnControls['segmentControls'][0]) #Snap it
        size = distance.returnBoundingBoxSize(d_returnControls['segmentControls'][0],True)#Get size
        log.debug(size)
        mc.scale(size[0]*1.1,size[1],size[2]*1.1,mi_crv.mNode,relative = True)
        
        #>>Copy tags and name
        mi_crv.addAttr('cgmName',attrType='string',value = 'cog')        
        mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
        mi_crv.doName()        

        #>>> Color
        curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])    
        
        d_returnControls['cog'] = mi_crv.mNode
        
    if 'hips' in controlTypes:
        if 'segmentControls' not in d_returnControls.keys():
            log.warn("Don't have hip creation without segment controls at present")
            return False
	
	distanceMult = .3
        
        #>>>Create the curve
        mi_crv = cgmMeta.cgmObject( curves.createControlCurve('semiSphere',1,'z-'))
        Snap.go(mi_crv, d_returnControls['segmentControls'][0],orient = True) #Snap it
        mi_crv.doGroup()
        if len(l_controlSnapObjects)>2:
            distanceToMove = distance.returnDistanceBetweenObjects(l_controlSnapObjects[0],l_controlSnapObjects[1])
            mi_crv.tz = -(distanceToMove*distanceMult)#Offset it
        
        #>Clean up group
        g = mi_crv.parent
        mi_crv.parent = False
        mc.delete(g)
        
        #>Size it
        size = distance.returnBoundingBoxSize(d_returnControls['segmentControls'][0],True)#Get size
        mi_obj = cgmMeta.cgmObject(d_returnControls['segmentControls'][0])
        d_size = returnBaseControlSize(mi_crv,bodyGeo[0],['z-'])      
        log.debug(size)
        mc.scale(size[0],size[2],(size[1]),mi_crv.mNode,os = True, relative = True)
        mi_crv.sz = d_size['z'] * 1.25
        mc.makeIdentity(mi_crv.mNode,apply=True, scale=True)
        
        #>>Copy tags and name
        mi_crv.addAttr('cgmName',attrType='string',value = 'hips')        
        mi_crv.addAttr('cgmType',attrType='string',value = 'controlAnim')
        mi_crv.doName()  
        
        #>>> Color
        curves.setCurveColorByName(mi_crv.mNode,l_moduleColors[0])        

        d_returnControls['hips'] = mi_crv.mNode
        
    """
        
        mc.makeIdentity(cogControl,apply=True, scale=True)
        """
    
    return d_returnControls
'''

"""
def limbControlMakerBAK(moduleNull,controlTypes = ['cog']):
    # 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    * Save the new positional information from the template objects
    * Collect all names of objects for a delete list
    * If anything in the module doesn't belong there, un parent it, report it
        * like a template object parented to another obect

    ARGUMENTS:
    moduleNull(string)
    controlTypes(list) = ['option1','option2']
    
    RETURNS:
    limbJoints(list)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #   
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Gather data
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # control helper objects - distance sorted#
    templateRoot =  modules.returnInfoNullObjects(moduleNull,'templatePosObjects',types='templateRoot')
    controlTemplateObjects =  modules.returnInfoNullObjects(moduleNull,'templateControlObjects',types='all')
    controlTemplateObjects = distance.returnDistanceSortedList(templateRoot,controlTemplateObjects)

    #size list of template control objects #
    controlTemplateObjectsSizes = []
    for obj in controlTemplateObjects:
        controlTemplateObjectsSizes.append(distance.returnAbsoluteSizeCurve(obj))
    
    # pos objects - distance sorted #
    posTemplateObjects =  modules.returnInfoNullObjects(moduleNull,'templatePosObjects',types='templateObject')
    posTemplateObjects = distance.returnDistanceSortedList(templateRoot,posTemplateObjects)

    
    # orientation objects - distance sorted #
    orientationTemplateObjects = []
    for obj in posTemplateObjects:
        orientationTemplateObjects.append(attributes.returnMessageObject(obj,'orientHelper'))
    
    orientationTemplateObjects = distance.returnDistanceSortedList(templateRoot,orientationTemplateObjects)
    

    returnControls = {}
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #>>> Control Maker
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    if 'spineIKHandle' in controlTypes:
        # initial create#
        ikHandleCurve = curves.createControlCurve('circleArrow2',1)
        mc.setAttr((ikHandleCurve+'.rz'),90)
        mc.setAttr((ikHandleCurve+'.ry'),90)
        mc.makeIdentity(ikHandleCurve, apply = True, r=True)
        startSizeBuffer = controlTemplateObjectsSizes[-1]
        scaleFactor = startSizeBuffer[0] * 1.25
        mc.setAttr((ikHandleCurve+'.sx'),1)
        mc.setAttr((ikHandleCurve+'.sy'),scaleFactor)
        mc.setAttr((ikHandleCurve+'.sz'),scaleFactor)
        position.moveParentSnap(ikHandleCurve,controlTemplateObjects[-1])
        position.movePointSnap(ikHandleCurve,orientationTemplateObjects[-1])
        
        # make our transform #
        transform = rigging.groupMeObject(controlTemplateObjects[-1],False)
        
        # connects shape #
        curves.parentShapeInPlace(transform,ikHandleCurve)
        mc.delete(ikHandleCurve)
        
        # copy over the pivot we want #
        rigging.copyPivot(transform,orientationTemplateObjects[-1])
        
        # Store data and name#
        attributes.copyUserAttrs(controlTemplateObjects[-1],transform,attrsToCopy=['cgmName'])
        attributes.storeInfo(transform,'cgmType','controlAnim')
        attributes.storeInfo(transform,'cgmTypeModifier','ik')
        transform = NameFactory.doNameObject(transform)
        returnControls['spineIKHandle'] = transform
    
    if 'ikHandle' in controlTypes:
        # initial create#
        ikHandleCurve = curves.createControlCurve('cube',1)
        endSizeBuffer = controlTemplateObjectsSizes[-1]
        mc.setAttr((ikHandleCurve+'.sx'),endSizeBuffer[0])
        mc.setAttr((ikHandleCurve+'.sy'),endSizeBuffer[1])
        mc.setAttr((ikHandleCurve+'.sz'),endSizeBuffer[1])
        position.moveParentSnap(ikHandleCurve,controlTemplateObjects[-1])
        position.movePointSnap(ikHandleCurve,orientationTemplateObjects[-1])
        
        # make our transform #
        transform = rigging.groupMeObject(controlTemplateObjects[-1],False)
        
        # connects shape #
        curves.parentShapeInPlace(transform,ikHandleCurve)
        mc.delete(ikHandleCurve)
        
        # copy over the pivot we want #
        rigging.copyPivot(transform,orientationTemplateObjects[-1])
        
        # Store data and name#
        attributes.copyUserAttrs(controlTemplateObjects[-1],transform,attrsToCopy=['cgmName'])
        attributes.storeInfo(transform,'cgmType','controlAnim')
        attributes.storeInfo(transform,'cgmTypeModifier','ik')
        transform = NameFactory.doNameObject(transform)
        returnControls['ikHandle'] = transform
        
    if 'twistFix' in controlTypes:
        # initial create#
        twistCurve = curves.createControlCurve('circleArrow1',1,'y+')
        startSizeBuffer = controlTemplateObjectsSizes[0]
        scaleFactor = startSizeBuffer[0] * 1.25
        mc.setAttr((twistCurve+'.sx'),1)
        mc.setAttr((twistCurve+'.sy'),scaleFactor)
        mc.setAttr((twistCurve+'.sz'),scaleFactor)
        position.moveParentSnap(twistCurve,orientationTemplateObjects[0])

        # make our transform #
        transform = rigging.groupMeObject(controlTemplateObjects[0],False)
        
        # connects shape #
        curves.parentShapeInPlace(transform,twistCurve)
        mc.delete(twistCurve)
        
        # copy over the pivot we want #
        rigging.copyPivot(transform,orientationTemplateObjects[0])
        
        # Store data and name#
        attributes.copyUserAttrs(controlTemplateObjects[0],transform,attrsToCopy=['cgmName'])
        attributes.storeInfo(transform,'cgmType','controlAnim')
        attributes.storeInfo(transform,'cgmTypeModifier','twist')
        transform = NameFactory.doNameObject(transform)
        returnControls['twistFix'] = transform
     
    if 'vectorHandleSpheres' in controlTypes:
        vectorHandles = []
        for obj in controlTemplateObjects[1:-1]:
            vectorHandleBuffer = []
            currentIndex = controlTemplateObjects.index(obj)
            vectorHandleCurve = curves.createControlCurve('sphere',1)
            sizeBuffer = controlTemplateObjectsSizes[currentIndex]
            scaleFactor = sizeBuffer[0]*.75
            mc.setAttr((vectorHandleCurve+'.sx'),scaleFactor)
            mc.setAttr((vectorHandleCurve+'.sy'),scaleFactor)
            mc.setAttr((vectorHandleCurve+'.sz'),scaleFactor)
            position.moveParentSnap(vectorHandleCurve,orientationTemplateObjects[currentIndex])
            
            # make our transform #
            transform = rigging.groupMeObject(obj,False)
            
            # connects shape #
            curves.parentShapeInPlace(transform,vectorHandleCurve)
            mc.delete(vectorHandleCurve)
            
            # copy over the pivot we want #
            rigging.copyPivot(transform,orientationTemplateObjects[currentIndex])
            
            # Store data and name#
            attributes.copyUserAttrs(obj,transform,attrsToCopy=['cgmName'])
            attributes.storeInfo(transform,'cgmType','controlAnim')
            attributes.storeInfo(transform,'cgmTypeModifier','ik')
            vectorHandleBuffer = NameFactory.doNameObject(transform)
            vectorHandles.append(vectorHandleBuffer)
            
            
        returnControls['vectorHandleSpheres'] = vectorHandles
        
    if 'vectorHandles' in controlTypes:
        vectorHandles = []
        for obj in controlTemplateObjects[1:-1]:
            vectorHandleBuffer = []
            currentIndex = controlTemplateObjects.index(obj)
            vectorHandleCurve = curves.createControlCurve('circleArrow',1)
            mc.setAttr((vectorHandleCurve+'.rx'),90)
            mc.makeIdentity(vectorHandleCurve, apply = True, r=True)
            sizeBuffer = controlTemplateObjectsSizes[currentIndex]
            scaleFactor = sizeBuffer[0]*1.5
            mc.setAttr((vectorHandleCurve+'.sx'),scaleFactor)
            mc.setAttr((vectorHandleCurve+'.sy'),scaleFactor)
            mc.setAttr((vectorHandleCurve+'.sz'),scaleFactor)
            position.moveParentSnap(vectorHandleCurve,controlTemplateObjects[currentIndex])
            position.movePointSnap(vectorHandleCurve,orientationTemplateObjects[currentIndex])
            
            # make our transform #
            transform = rigging.groupMeObject(obj,False)
            
            # connects shape #
            curves.parentShapeInPlace(transform,vectorHandleCurve)
            mc.delete(vectorHandleCurve)
            
            # copy over the pivot we want #
            rigging.copyPivot(transform,orientationTemplateObjects[currentIndex])
            
            # Store data and name#
            attributes.copyUserAttrs(obj,transform,attrsToCopy=['cgmName'])
            attributes.storeInfo(transform,'cgmType','controlAnim')
            attributes.storeInfo(transform,'cgmTypeModifier','ik')
            vectorHandleBuffer = NameFactory.doNameObject(transform)
            vectorHandles.append(vectorHandleBuffer)
            
            
        returnControls['vectorHandles'] = vectorHandles
        
    if 'hips' in controlTypes:
        hipsCurve = curves.createControlCurve('semiSphere',1)
        mc.setAttr((hipsCurve+'.rx'),90)
        mc.makeIdentity(hipsCurve,apply=True,translate =True, rotate = True, scale=True)
        rootSizeBuffer = controlTemplateObjectsSizes[0]
        mc.setAttr((hipsCurve+'.sx'),rootSizeBuffer[0])
        mc.setAttr((hipsCurve+'.sy'),rootSizeBuffer[1])
        mc.setAttr((hipsCurve+'.sz'),rootSizeBuffer[0])
        position.moveParentSnap(hipsCurve,controlTemplateObjects[0])
        
        # make our transform #
        transform = rigging.groupMeObject(controlTemplateObjects[0],False)
        
        # connects shape #
        curves.parentShapeInPlace(transform,hipsCurve)
        mc.delete(hipsCurve)
        
        # Store data and name#
        attributes.storeInfo(transform,'cgmName','hips')
        attributes.storeInfo(transform,'cgmType','controlAnim')
        hips = NameFactory.doNameObject(transform)
        returnControls['hips'] = hips
            
    if 'cog' in controlTypes:
        cogControl = curves.createControlCurve('cube',1)
        rootSizeBuffer = controlTemplateObjectsSizes[0]
        mc.setAttr((cogControl+'.sx'),rootSizeBuffer[0]*1.05)
        mc.setAttr((cogControl+'.sy'),rootSizeBuffer[1]*1.05)
        mc.setAttr((cogControl+'.sz'),rootSizeBuffer[0]*.25)
        position.moveParentSnap(cogControl,controlTemplateObjects[0])
        
        mc.makeIdentity(cogControl,apply=True, scale=True)
        
        # Store data and name#
        attributes.storeInfo(cogControl,'cgmName','cog')
        attributes.storeInfo(cogControl,'cgmType','controlAnim')
        cogControl = NameFactory.doNameObject(cogControl)
        returnControls['cog'] = cogControl
    

    if 'limbControls' in controlTypes:
        limbControls = []
        controlSegments = lists.parseListToPairs(controlTemplateObjects)
        orientationSegments = lists.parseListToPairs(orientationTemplateObjects)
        cnt = 0
        for segment in controlSegments:
            # get our orientation segment buffer #
            orientationSegment = orientationSegments[cnt]
            #move distance #
            distanceToMove = distance.returnDistanceBetweenObjects(orientationSegment[0],orientationSegment[1])

            # root curve #
            rootCurve = curves.createControlCurve('circle',1)
            rootSizeBuffer = distance.returnAbsoluteSizeCurve(segment[0])
            mc.setAttr((rootCurve+'.sx'),rootSizeBuffer[0])
            mc.setAttr((rootCurve+'.sy'),rootSizeBuffer[1])
            mc.setAttr((rootCurve+'.sz'),1)
            position.moveParentSnap(rootCurve,segment[0])
            #mc.move(0, 0, (distanceToMove * .15), rootCurve, r=True,os=True,wd=True)
            
            # end curve #
            endCurve = curves.createControlCurve('circle',1)
            rootSizeBuffer = distance.returnAbsoluteSizeCurve(segment[1])
            mc.setAttr((endCurve+'.sx'),rootSizeBuffer[0])
            mc.setAttr((endCurve+'.sy'),rootSizeBuffer[1])
            mc.setAttr((endCurve+'.sz'),1)
            position.moveParentSnap(endCurve,segment[1])
            position.movePointSnap(endCurve,orientationSegment[1])
            mc.move(0, 0, -(distanceToMove * .15), endCurve, r=True,os=True,wd=True)
            
            #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            #>>> Side curves
            #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            # locators on curve#
            side1Locs = []
            side2Locs = []
            frontLocs = []
            backLocs = []
            side1Locs.append(locators.locMeCvFromCvIndex(rootCurve,3))
            side1Locs.append(locators.locMeCvFromCvIndex(endCurve,3))
            side2Locs.append(locators.locMeCvFromCvIndex(rootCurve,7))
            side2Locs.append(locators.locMeCvFromCvIndex(endCurve,7))
            frontLocs.append(locators.locMeCvFromCvIndex(rootCurve,5))
            frontLocs.append(locators.locMeCvFromCvIndex(endCurve,5))
            backLocs.append(locators.locMeCvFromCvIndex(rootCurve,0))
            backLocs.append(locators.locMeCvFromCvIndex(endCurve,0))
            
            # get u positions for new curves#
            side1PosSet = []
            side2PosSet = []
            frontPosSet = []
            backPosSet = []
            side1PosSet.append(distance.returnClosestUPosition(side1Locs[0],rootCurve))
            side1PosSet.append(distance.returnClosestUPosition(side1Locs[1],endCurve))
            side2PosSet.append(distance.returnClosestUPosition(side2Locs[0],rootCurve))
            side2PosSet.append(distance.returnClosestUPosition(side2Locs[1],endCurve))
            frontPosSet.append(distance.returnClosestUPosition(frontLocs[0],rootCurve))
            frontPosSet.append(distance.returnClosestUPosition(frontLocs[1],endCurve))
            backPosSet.append(distance.returnClosestUPosition(backLocs[0],rootCurve))
            backPosSet.append(distance.returnClosestUPosition(backLocs[1],endCurve))

            # make side curves#
            sideCrv1 = mc.curve (d=1, p = side1PosSet , os=True)
            sideCrv2 = mc.curve (d=1, p = side2PosSet , os=True)
            frontCrv = mc.curve (d=1, p = frontPosSet , os=True)
            backCrv = mc.curve (d=1, p = backPosSet , os=True)
            
            # combine curves #
            mc.makeIdentity(rootCurve,apply=True,translate =True, rotate = True, scale=True)
            mc.makeIdentity(endCurve,apply=True,translate =True, rotate = True, scale=True)
            segmentCurveBuffer = curves.combineCurves([sideCrv1,sideCrv2,frontCrv,backCrv,rootCurve,endCurve])
            
            # delete locs #
            for loc in side1Locs,side2Locs,frontLocs,backLocs:
                mc.delete(loc)
                
            # make our transform #
            transform = rigging.groupMeObject(segment[0],False)
            
            # connects shape #
            curves.parentShapeInPlace(transform,segmentCurveBuffer)
            mc.delete(segmentCurveBuffer)
            
            # copy over the pivot we want #
            rigging.copyPivot(transform,orientationSegment[0])

                
            # Store data and name#
            attributes.copyUserAttrs(segment[0],transform,attrsToCopy=['cgmName'])
            attributes.storeInfo(transform,'cgmType','controlAnim')
            attributes.storeInfo(transform,'cgmTypeModifier','fk')
            limbControlBuffer = NameFactory.doNameObject(transform)
            limbControls.append(limbControlBuffer)
            
            cnt+=1
        returnControls['limbControls'] = limbControls
        
    if 'headControls' in controlTypes:
        headControls = []
        controlSegments = lists.parseListToPairs(controlTemplateObjects)
        orientationSegments = lists.parseListToPairs(orientationTemplateObjects)
        # figure out our second to last segment to do something a bit different #
        secondToLastCheck = (len(controlSegments)-2)
        print secondToLastCheck  
        cnt = 0
        for segment in controlSegments:
            # get our orientation segment buffer #
            orientationSegment = orientationSegments[cnt]            
            #move distance #
            distanceToMove = distance.returnDistanceBetweenObjects(segment[0],segment[1])

            # root curve #
            rootCurve = curves.createControlCurve('circle',1)
            rootSizeBuffer = distance.returnAbsoluteSizeCurve(segment[0])
            mc.setAttr((rootCurve+'.sx'),rootSizeBuffer[0])
            mc.setAttr((rootCurve+'.sy'),rootSizeBuffer[1])
            mc.setAttr((rootCurve+'.sz'),1)
            position.moveParentSnap(rootCurve,segment[0])
            mc.move(0, 0, (distanceToMove * .05), rootCurve, r=True,os=True,wd=True)
            
            # end curve #
            endCurve = curves.createControlCurve('circle',1)
            if cnt != secondToLastCheck:
                rootSizeBuffer = distance.returnAbsoluteSizeCurve(segment[1])
            else:
                rootSizeBuffer = distance.returnAbsoluteSizeCurve(segment[0])
            mc.setAttr((endCurve+'.sx'),rootSizeBuffer[0])
            mc.setAttr((endCurve+'.sy'),rootSizeBuffer[1])
            mc.setAttr((endCurve+'.sz'),1)
            position.moveParentSnap(endCurve,segment[1])
            mc.move(0, 0, -(distanceToMove * .05), endCurve, r=True,os=True,wd=True)
            
            #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            #>>> Side curves
            #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            # locators on curve#
            side1Locs = []
            side2Locs = []
            frontLocs = []
            backLocs = []
            side1Locs.append(locators.locMeCvFromCvIndex(rootCurve,3))
            side1Locs.append(locators.locMeCvFromCvIndex(endCurve,3))
            side2Locs.append(locators.locMeCvFromCvIndex(rootCurve,7))
            side2Locs.append(locators.locMeCvFromCvIndex(endCurve,7))
            frontLocs.append(locators.locMeCvFromCvIndex(rootCurve,5))
            frontLocs.append(locators.locMeCvFromCvIndex(endCurve,5))
            backLocs.append(locators.locMeCvFromCvIndex(rootCurve,0))
            backLocs.append(locators.locMeCvFromCvIndex(endCurve,0))
            
            # get u positions for new curves#
            side1PosSet = []
            side2PosSet = []
            frontPosSet = []
            backPosSet = []
            side1PosSet.append(distance.returnClosestUPosition(side1Locs[0],rootCurve))
            side1PosSet.append(distance.returnClosestUPosition(side1Locs[1],endCurve))
            side2PosSet.append(distance.returnClosestUPosition(side2Locs[0],rootCurve))
            side2PosSet.append(distance.returnClosestUPosition(side2Locs[1],endCurve))
            frontPosSet.append(distance.returnClosestUPosition(frontLocs[0],rootCurve))
            frontPosSet.append(distance.returnClosestUPosition(frontLocs[1],endCurve))
            backPosSet.append(distance.returnClosestUPosition(backLocs[0],rootCurve))
            backPosSet.append(distance.returnClosestUPosition(backLocs[1],endCurve))

            # make side curves#
            sideCrv1 = mc.curve (d=1, p = side1PosSet , os=True)
            sideCrv2 = mc.curve (d=1, p = side2PosSet , os=True)
            frontCrv = mc.curve (d=1, p = frontPosSet , os=True)
            backCrv = mc.curve (d=1, p = backPosSet , os=True)
            
            # combine curves #
            mc.makeIdentity(rootCurve,apply=True,translate =True, rotate = True, scale=True)
            mc.makeIdentity(endCurve,apply=True,translate =True, rotate = True, scale=True)
            segmentCurveBuffer = curves.combineCurves([sideCrv1,sideCrv2,frontCrv,backCrv,rootCurve,endCurve])
            
            # delete locs #
            for loc in side1Locs,side2Locs,frontLocs,backLocs:
                mc.delete(loc)
                
            # make our transform #
            transform = rigging.groupMeObject(segment[0],False)
            
            # connects shape #
            curves.parentShapeInPlace(transform,segmentCurveBuffer)
            mc.delete(segmentCurveBuffer)
            
            # copy over the pivot we want #
            rigging.copyPivot(transform,orientationSegment[0])
              
            # Store data and name#
            attributes.copyUserAttrs(segment[0],transform,attrsToCopy=['cgmName'])
            attributes.storeInfo(transform,'cgmType','controlAnim')
            attributes.storeInfo(transform,'cgmTypeModifier','fk')
            segmentCurveBuffer = NameFactory.doNameObject(transform)
            headControls.append(segmentCurveBuffer)
            
            cnt+=1
        returnControls['headControls'] = headControls

    
    return returnControls"""


    
    