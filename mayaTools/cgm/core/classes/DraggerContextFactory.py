#=================================================================================================================================================
#=================================================================================================================================================
#	DraggerContextFactory - a part of cgmTools
#=================================================================================================================================================
#=================================================================================================================================================
#
# DESCRIPTION:
#	Classes and functions for DraggerContext
#
# AUTHOR:
# 	Josh Burton
#	http://www.cgmonks.com
# 	Copyright 2012 CG Monks - All Rights Reserved.
#
# ACKNOWLEDGEMENTS:
#   Morgan Loomis
# 	http://forums.cgsociety.org/archive/index.php/t-983068.html
# 	http://forums.cgsociety.org/archive/index.php/t-1002257.html
# 	https://groups.google.com/forum/?fromgroups#!topic/python_inside_maya/n6aJq27fg0o%5B1-25%5D
#======================================================================================================================
import time
import maya.cmds as mc
import copy
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as om
from cgm.core import cgm_Meta as cgmMeta
from cgm.core.rigger.lib import joint_Utils as jntUtils
from cgm.core.lib import rayCaster as RayCast
from cgm.core import cgm_General as cgmGen
from cgm.core.cgmPy import validateArgs as cgmValid
from cgm.core.lib import search_utils as SEARCH
from cgm.core.lib import distance_utils as DIST
from cgm.core.lib import position_utils as POS
from cgm.core.lib import node_utils as NODES
from cgm.core.lib import name_utils as NAMES
reload(POS)
reload(NODES)
from cgm.core.lib import math_utils as MATHUTILS
from cgm.core.lib import locator_utils as LOC
reload(RayCast)
from cgm.lib import (locators,
                     geo,
                     curves,
                     search,
                     attributes,
                     lists,
                     nodes,
                     rigging,
                     distance,
                     guiFactory)
reload(distance)
reload(curves)
import os

#========================================================================
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
#========================================================================

class ContextualPick(object):
    def __init__(self,name = 'cgmDraggerContext', *a,**kws):
        """ 
        Initializes a draggerContext object for use with other tools

        Arguments:
        undoMode --
        projection --
        plane --
        space --
        cursor
        drag -- Whether to enable drag mode
        """
        self.undoMode = kws.pop('undoMode','step')
        self.projection = kws.pop('projection','plane')
        self.plane = kws.pop('plane',[1,0,0])
        self.space = kws.pop('space','world')
        self.cursor = kws.pop('cursor','crossHair')
        self.dragOption = kws.pop('drag',False)

        self.name = name
        self.l_return = []

        self.build(*a,**kws )
        self.setTool()

    def build(self,*a,**kws ):
        if mc.draggerContext(self.name,query=True,exists=True): # if it exists, delete it
            mc.setToolTo('selectSuperContext')        
            mc.selectMode(object=True)             
            mc.deleteUI(self.name)  

        imageFilePath = ('cgmDefault.png')

        mc.draggerContext( self.name,  image1 = imageFilePath,
                           undoMode = self.undoMode, projection = self.projection, space = self.space,
                           initialize = self.initialPress,
                           pressCommand = self.press,
                           releaseCommand = self.release,
                           finalize = self.finalize,
                           *a,**kws )

        if self.projection == 'plane': mc.draggerContext(self.name,e=True, plane = self.plane)# if our projection is 'plane', set the plane
        if self.dragOption:mc.draggerContext(self.name,e=True, dragCommand = self.drag)# If drag mode, turn it on


    def finalize(self):pass


    def press(self):
        if not mc.draggerContext(self.name,query=True,exists=True): # if it exists, delete it       
            self.build
            self.setTool()            

        self.anchorPoint = mc.draggerContext(self.name, query=True, anchorPoint=True)
        self.modifier = mc.draggerContext(self.name, query=True, modifier=True)
        self.button = mc.draggerContext(self.name, query=True, button=True)

        self.x = self.anchorPoint[0]
        self.y = self.anchorPoint[1]
        self.z = self.anchorPoint[2]

        #log.info("Position is %s in '%s' space"%(self.anchorPoint,self.space))

    def release(self):pass

    def drag(self):
        self.dragPoint = mc.draggerContext(self.name, query=True, dragPoint=True)
        self.button = mc.draggerContext( self.name, query=True, button=True)
        self.modifier = mc.draggerContext( self.name, query=True, modifier=True)

        self.x = self.dragPoint[0]
        self.y = self.dragPoint[1]
        self.z = self.dragPoint[2]

    def initialPress(self):pass

    def dropTool(self):
        mc.setToolTo('selectSuperContext')        
        mc.selectMode(object=True)

    def setTool(self):
        mc.setToolTo(self.name)

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Subclasses
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
_clickMesh_modes = ['surface','intersections','midPoint']
class clickMesh(ContextualPick):
    """
    Find positional data from clicking on a surface from a ContextualPick instance.
    And other things...:)

    :parameters:
        mesh(list) -- Mesh/nurbsSurfaces to cast to. If None, will use all visible mesh.
        mode(string) -- options:('surface' is default)
                        'surface' -- Single return
                        'intersections' -- all hits on the vector ray
                        'midPoint' -- mid point of intersections
    
        create(False/option) -- options:('locator' is default)
                                'locator' -- makes a locator 
                                'joint' -- creates joints per click
                                'jointChain' -- rebuilds all positions as a chain at tool exit
                                'curve' -- builds curve from positions at tool exit
                                'group' -- build groups at positions
                                'follicle' --creates a folicle
    
        closestOnly(bool) -- only return the closest hit from all mesh hits (default - True)
        clampIntersections(False/int) -- clamp number of interactions
        dragStore(bool) -- whether to force store data during drag
        maxStore(int) -- Maximum number of hits to accept before finalizing
        posOffset(vector) -- x,y,z offset from given point
        offsetDistance(float) -- amount to offset for distance offsetMode
        toDuplicate(list) -- objects to duplicate
        offsetMode(str) -- 'vector','normal' (default -- 'vector')
                            distance -- offset along the ray with the end - start being the base distance
                            snapCast -- An auto guessing post cast mode to attempt to keep things off the surface when casting
        clampValues(vector) -- clamp given values to provided ones. Useful for a spine cast for example
        orientSnap(bool) -- orient the created object to surface
        timeDelay(float) -- Wait to start the tool after a given delay. Useful for marking menu calling
        tagAndName(dict) -- I don't remember...:)
        toCreate(list) -- list of items names to make, sets's max as well. When it's through the list, it shops
        toSnap(list) -- objects to snap to a final pos value

    :Stores
    self.l_pos(list) -- points on the surface selected in world space

    TODO:
    Add depth option
    """  
    def __init__(self,
                 mode = 'surface',
                 mesh = None,
                 create = False,
                 closestOnly = True,
                 clampIntersections = False,
                 dragStore = False,
                 maxStore = False,
                 posOffset = None,
                 offsetMode = None,        
                 offsetDistance = 1.0,
                 clampValues = [None,None,None],
                 orientSnap = True,
                 timeDelay = None,
                 tagAndName = {},
                 toCreate = [],
                 toDuplicate = [],
                 toSnap = [],#...objects to snap on release
                 *a,**kws):

        _str_funcName = 'clickMesh.__init__'
        log.debug(">>> %s >> "%_str_funcName + "="*75)     	
        #>>> Store our info ====================================================================
        self._createModes = ['locator','joint','jointChain','curve','follicle','group',False]
        self._l_modes = _clickMesh_modes
        self.l_mesh = []
        self.d_meshPos = {} #creating this pretty much just for follicle mode so we can attache to a specific mesh
        self.d_meshUV = {}
        self.f_meshArea = 1
        self.l_toSnap = cgmValid.listArg(toSnap)
        self._createMode = create
        self._getUV = False
        self._time_start = time.clock()
        self._time_delayCheck = timeDelay
        self._l_folliclesToMake = []
        self._l_folliclesBuffer = []
        self._l_toDuplicate = toDuplicate
        if self._createMode == 'follicle':#Only get uv intersection for follicles
            self._getUV = True

        self.b_closestOnly = closestOnly
        self.l_created = []
        self.b_clampSetting = clampIntersections
        self.b_dragStoreMode = dragStore
        self.l_return = []
        self.l_returnRaw = []
        self.d_tagAndName = tagAndName
        self._posBuffer = False
        self.v_posOffset = posOffset or False    
        self.str_offsetMode = offsetMode
        self.f_offsetDistance = offsetDistance
        self.b_orientSnap = orientSnap
        self._createModeBuffer = False
        self.int_maxStore = maxStore
        self.l_toCreate = toCreate
        self.v_clampValues = clampValues
        if toCreate:
            self.int_maxStore = len(toCreate)

        self.setMode(mode)
               
        ContextualPick.__init__(self, drag = True, space = 'screen',projection = 'viewPlane', *a,**kws )

        if mesh is None:
            log.info("Using all visible mesh!")
            for l in mc.ls(type='mesh',visible = True), mc.ls(type='nurbsSurface',visible = True):
                for o in l:
                    self.addTargetMesh( o )#             
        if mesh is not None:
            assert type(mesh) is list,"Mesh call must be in list form when called"
            for m in mesh:
                self.addTargetMesh(m)    
        self.updateMeshArea()

    def updateMeshArea(self):
        """
        Updates the mesh area of the added meshes (for sizing purposes)
        """
        self.f_meshArea = 1
        buffer = []
        for m in self.l_mesh:
            buffer.append(distance.returnObjectSize(m))

        if buffer:
            self.f_meshArea = sum(buffer)/len(buffer)
            
    def add_toDuplicate(self,objs):
        _str_func = 'add_toDuplicate'
        for obj in objs:
            _transform = SEARCH.get_transform(obj)
            if _transform and _transform not in self._l_toDuplicate:
                log.info("|{0}| >> Added to toDuplicate: {1}".format(_str_func,obj))
                self._l_toDuplicate.append(obj)

            
    def addTargetMesh(self,mesh):
        """
        Add target mesh to the tool
        """
        if not mc.objExists(mesh):
            log.warning("'%s' doesn't exist. Ignoring..."%mesh)
            return False

        if mesh not in self.l_mesh:
            buffer = cgmValid.get_mayaType(mesh)
            if buffer in ['mesh','nurbsSurface']:
                self.l_mesh.append(mesh)
                #self.updateMeshArea()
                return True
            else:
                log.warning("'%s' is not a mesh. It is returning as '%s'"%(mesh,buffer))
                return False
        return False

    def removeTargetMesh(self,mesh):
        """
        Remove target mesh to the tool
        """
        if mesh in self.l_mesh:
            self.l_mesh.remove(mesh) 
            log.info("'%s' removed from '%s'"%(mesh,self.name))

    def setMode(self,mode):
        """
        Set tool mode
        """
        #assert mode in ['surface','intersections','midPoint'],"'%s' not a defined mode"%mode
        self.mode = cgmValid.kw_fromList(mode, ['surface','intersections','midPoint','far'],indexCallable=True) 

    def setClamp(self,setting):
        """
        Set clamp setting
        """
        assert type(setting) is int or setting is False,"'%s' is not a valid setting"%setting 
        self.b_clampSetting = setting

    def setCreate(self,create):
        """
        Set tool mode
        """
        assert create in self._createModes,"'%s' is not a valid create mode"%create    
        self._createMode = create
        if self._createMode == 'follicle':#Only get uv intersection for follicles
            self._getUV = True            

    def setDragStoreMode(self,mode):
        """
        Set drag update mode
        """
        assert bool(mode) in [True,False],"'%s' should be a bool"%mode                 
        self.b_dragStoreMode = mode
        log.warning("Drag store is %s!"%mode)

    def reset(self):
        """
        Reset data
        """
        self.l_created = []
        self.l_return = []

        log.debug("'%s' reset."%self.name)

    def setTool(self):
        ContextualPick.setTool(self)

    def dropTool(self):
        mc.setToolTo('selectSuperContext')        
        mc.selectMode(object=True)
        mc.refresh()

    def press(self):
        """
        Press action. Clears buffers.
        """            
        ContextualPick.press(self)
        self._createModeBuffer = []
        self.updatePos()

    def finalize(self):
        """
        Press action. Clears buffers.
        """
        #Clean our lists...
        _str_funcName = 'finalize'
        self.l_created = lists.returnListNoDuplicates(self.l_created)
        self.l_return = lists.returnListNoDuplicates(self.l_return)

        if self._createMode in ['curve','jointChain','group','follicle'] and self.l_return:
            if self._createMode == 'group':
                bufferList = []
                for i,o in enumerate(self.l_created):
                    buffer = rigging.groupMeObject(o,False)
                    bufferList.append(buffer)                    
                    try:mc.delete(o)
                    except:pass
                self.l_created = bufferList

            elif self._createMode =='follicle':
                #...Get our follicle uvs here.
                log.debug("|{0}| follicle uv search...".format(_str_funcName))
                
                for pos in self.l_returnRaw:
                    log.debug("|{0}|...pos {1}".format(_str_funcName,pos))                
                    for i,m in enumerate(self.d_meshPos.keys()):
                        log.debug("|{0}|...mesh: {1}".format(_str_funcName,m))                                    
                        for i2,h in enumerate(self.d_meshPos[m]):
                            if h == pos:
                                log.debug("Found follicle match!")
                                try:
                                    _set = [m, self.d_meshUV[m][i2], "{0}_u{1}s_v{2}".format(NAMES.get_short(m),self.d_meshUV[m][i2][0],self.d_meshUV[m][i2][1])]
                                    self._l_folliclesToMake.append(_set)
                                    log.debug("|{0}|...uv {1}".format(_str_funcName,_set))                                                
                                except Exception,err:
                                    log.error("|{0}| >> Failed to query uv for hit {2} on shape {2} | err:{1}".format(_str_funcName,err,pos,m))                

                
                if self._l_folliclesToMake:
                    for f_dat in self._l_folliclesToMake:
                        _follicle = NODES.add_follicle(f_dat[0],f_dat[2])
                        log.info("Follicle created: {0}".format(_follicle))                        
                        attributes.doSetAttr(_follicle[0],'parameterU',f_dat[1][0])
                        attributes.doSetAttr(_follicle[0],'parameterV',f_dat[1][1])                    
                        """bufferList = []
                        for o in self.l_created:
                    mesh = attributes.doGetAttr(o,'cgmHitTarget')
                    if mc.objExists(mesh):
                        uv = distance.returnClosestUVToPos(mesh,distance.returnWorldSpacePosition(o))
                        log.info("uv: {0}".format(uv))
                        follicle = nodes.createFollicleOnMesh(mesh)
                        log.info("follicle: {0}".format(follicle))                        
                        attributes.doSetAttr(follicle[0],'parameterU',uv[0])
                        attributes.doSetAttr(follicle[0],'parameterV',uv[1])
                        try:mc.delete(o)
                        except:pass   """   
                try:mc.delete(self.l_created)
                except:pass 
            else:
                for o in self.l_created:
                    try:mc.delete(o)
                    except:pass
                if self._createMode == 'curve' and len(self.l_return)>1:
                    if len(self.l_return) > 1:
                        #self.l_created = [curves.curveFromPosList(self.l_return)]
                        #self.l_created = [ mc.curve (d=3, ep = self.l_return , ws=True, )]
                        knot_len = len(self.l_return)+3-1		
                        curveBuffer = mc.curve (d=3, ep = self.l_return, k = [i for i in range(0,knot_len)], os=True)   
                        self.l_created = [curveBuffer]
                    else:
                        log.warning("Need at least 2 points for a curve")                        
                elif self._createMode == 'jointChain':
                    self.l_created = []
                    mc.select(cl=True)
                    for pos in self.l_return:                             
                        self.l_created.append( mc.joint (p = (pos[0], pos[1], pos[2]),radius = 1) ) 
        log.debug( self.l_created)

        if self.d_tagAndName:
            for o in self.l_created:
                try:
                    i_o = cgmMeta.cgmNode(o)
                    for tag in self.d_tagAndName.keys():
                        i_o.doStore(tag,self.d_tagAndName[tag])
                    i_o.doName()
                except StandardError,error:
                    log.error(">>> clickMesh >> Failed to tag and name: %s | error: %s"%(i_o.p_nameShort,error))            	            		

        self.reset()        

    def release(self):
        """
        Store current data to return buffers
        """                            
        #Only store return values on release
        if not self.b_dragStoreMode:#If not on drag, do it here. Otherwise do it on update
            if self._posBuffer:
                self.l_return.extend(self._posBuffer)
                if self._posBufferRaw:
                    self.l_returnRaw.extend(self._posBufferRaw)
                else:
                    self.l_returnRaw.extend(self._posBuffer)
                    
            if self._createModeBuffer:
                self.l_created.extend(self._createModeBuffer)

        if self._posBuffer:
            log.debug("Position data : %s "%(self.l_return))
        if self._createModeBuffer:
            log.debug("Created : %s "%(self._createModeBuffer))
            mc.select(cl=True)

            #if 'joint' in self._createMode:
                #jntUtils.metaFreezeJointOrientation(self._createModeBuffer)	
        
        if self.l_created and self.l_toSnap and not self._l_toDuplicate:
            log.info("Snap Mode!")
          
            """
            #TESTING OFFSET
            _dist = DIST.get_distance_between_points(p,self.clickPos)
            log.info("BaseDistance: {0}".format(_dist))
            _dist = _dist - 1
            _newP = DIST.get_pos_by_vec_dist(self.clickPos,self.clickVector,_dist)
            log.info("Old point: {0} | new point: {1}".format(p,_newP))
            self._posBuffer[i] = _newP"""                              
            
            #Use that distance to subtract along our original ray's hit distance to get our new point
            for o in self.l_toSnap:
                _pos_base = POS.get(self.l_created[-1],pivot='rp',space='w')
                _pos = _pos_base 
                if self.str_offsetMode == 'snapCast':
                    try:
                        log.debug("snapCast: {0}".format(o))
                        
                        _pos_obj = POS.get(o,pivot='rp',space='w')#...Get the point of the object to snap
                        log.debug("startPoint: {0}".format(_pos_obj))
                        log.debug("posBuffer: {0}".format(_pos_base))
                        
                        _vec_obj = MATHUTILS.get_vector_of_two_points( _pos_obj,_pos_base)#...Get the vector from there to our hit
                        _dist_base = DIST.get_distance_between_points(_pos_base, _pos_obj)#...get our base distance
                        
                        _cast = RayCast.cast(self.l_mesh, startPoint=_pos_obj,vector=_vec_obj)
                        _nearHit = _cast['near']
                        _dist_firstHit = DIST.get_distance_between_points(_pos_obj,_nearHit)
                        log.debug("baseDist: {0}".format(_dist_base))
                        log.debug("firstHit: {0}".format(_dist_firstHit))
                        
                        if self.mode == 'far':
                            _dist_new = _dist_base + _dist_firstHit
                        else:
                            _dist_new = _dist_base - _dist_firstHit
                        _offsetPos = DIST.get_pos_by_vec_dist(_pos_obj,_vec_obj,(_dist_new))
                        
                        _pos = _offsetPos
                        
                        #Failsafe for casting to self...
                        if DIST.get_distance_between_points(_pos, _pos_obj) < _dist_firstHit:
                            log.warning("Close proximity cast, using default")
                            _pos = self._posBuffer[-1]
                    except Exception,err:
                        _pos = _pos_base                         
                        log.error("SnapCast fail. Using original pos... | err: {0}".format(err))
                try:
                    POS.set(o,_pos)
                except Exception,err:
                    log.error("{0} failed to snap. err: {1}".format(o,err))
            mc.delete(self.l_created)
            if self.l_toSnap:
                mc.select(self.l_toSnap)
            self.dropTool()
                
        if self.int_maxStore and len(self.l_return) == self.int_maxStore:
            log.debug("Max hit, finalizing")
            self.dropTool()


    def drag(self):
        """
        update positions
        """
        ContextualPick.drag(self)
        self.updatePos()

        if self._createModeBuffer:
            self.l_created.extend(self._createModeBuffer)          

    def getDistanceToCheck(self,m):
        assert mc.objExists(m), "'%s' doesn't exist. Couldn't check distance!"%m
        baseDistance = distance.returnDistanceBetweenPoints(self.clickPos, distance.returnWorldSpacePosition(m))
        baseSize = distance.returnBoundingBoxSize(m)

        return distance.returnWorldSpaceFromMayaSpace( baseDistance + sum(baseSize) )

    def convertPosToLocalSpace(self,pos):
        assert type(pos) is list,"'%s' is not a list. Coordinate expected"%pos
        returnList = []
        for f in pos:
            returnList.append( distance.returnMayaSpaceFromWorldSpace(f))
        return returnList

    def updatePos(self):
        """
        Get updated position data via shooting rays
        """
        _str_funcName = 'clickMesh.updatePos'
        log.debug(">>> %s >> "%_str_funcName + "="*75)     	
        if not self.l_mesh:
            return log.warning("No mesh objects have been added to '%s'"%(self.name)) 
        
        #_time = "%0.3f" %(time.clock() - self._time_start)
        if self._time_delayCheck is not None:
            _time =  float( "%0.3f" %(time.clock() - self._time_start) )
            #log.info("time {0} | delay: {1}".format(_time,self._time_delayCheck))
            if _time <= self._time_delayCheck:
                log.warning("Time delay, not starting...")
                if self.l_created:
                    mc.delete(self.l_created)                   
                return             
        buffer =  screenToWorld(int(self.x),int(self.y))#get world point and vector!

        self.clickPos = buffer[0] #Our world space click point
        self.clickVector = buffer[1] #Camera vector
        self._posBuffer = []#Clear our pos buffer
        self._posBufferRaw = []
        #checkDistance = self.getDistanceToCheck(m)
        checkDistance = 100000        
        
        kws = {'mesh':self.l_mesh,'startPoint':self.clickPos,'vector':self.clickVector,'maxDistance':checkDistance}
        if self.mode != 'surface':
            kws['firstHit'] = False
                        
        try:
            #buffer = RayCast.findMeshIntersection(m, self.clickPos , self.clickVector, checkDistance) 
            _res = RayCast.cast(**kws)
        except Exception,error:
            _res = None
            log.error("{0} >>> surface cast fail. More than likely, the offending face lacks uv's. Error:{1}".format(_str_funcName,error))
        
        if _res:
            try:
                for i,m in enumerate(_res['meshHits'].keys()):
                    #Buffer our data for processing on release....
                    if self.d_meshPos.has_key(m):
                        self.d_meshPos[m].extend(_res['meshHits'][m])
                    else:
                        self.d_meshPos[m] = _res['meshHits'][m]  
                        
                    _d_UVS = _res.get('uvs',{})
                    if _d_UVS:
                        if self.d_meshUV.has_key(m):
                            self.d_meshUV[m].extend(_d_UVS[m])
                        else:
                            self.d_meshUV[m] = _d_UVS[m]    
                            
                    #self.d_meshUV[m] = _d.get(m,[])
                    
                if self.mode == 'surface':
                    self._posBuffer = [_res['near']]
                elif self.mode == 'far':
                    self._posBuffer = [_res['far']]
                elif self.mode == 'midPoint':
                    if len(_res['hits']) < 2:
                        log.error("Must have two hits for midpoint mode")
                        return
                    
                    _near = _res['near']
                    _far = _res['far']
                    self._posBuffer = [ DIST.get_average_position([_near,_far]) ]
            except Exception,err:
                cgmGen.log_info_dict(_res,'Result')
                log.error("|{0}| >> Processing fail. err:{1}".format(_str_funcName,err))                
                return
        else:
            log.debug('No hits detected!')
            return    
        
        if not self._posBuffer:
            log.debug('No hits detected!')
            return
        
        if self.b_clampSetting and self.b_clampSetting < len(self._posBuffer):
            log.warning("Position buffer was clamped. Check settings if this was not desired.")
            self._posBuffer = distance.returnPositionDataDistanceSortedList(self.startPoint,self._posBuffer)
            self._posBuffer = self._posBuffer[:self.b_clampSetting]      
            
        #...Gonna do our offsets now
        self._posBufferRaw = copy.copy(self._posBuffer)        
        if self.mode not in ['midPoint']:
            if self.str_offsetMode == 'distance':
                log.debug("|{0}| >> offset by distance".format(_str_funcName))                
                self._posBufferRaw = copy.copy(self._posBuffer)
                _l = copy.copy(self._posBuffer)
                for i,pos in enumerate(self._posBuffer):
                    _p = RayCast.offset_hit_by_distance(pos,self.clickPos,self.clickVector,self.f_offsetDistance)
                    self._posBuffer[i] = _p
        
        if self.b_dragStoreMode:#If not on drag, do it here. Otherwise do it on update
            if self._posBuffer:
                self.l_return.extend(self._posBuffer)
                if self._posBufferRaw:
                    self.l_returnRaw.extend(self._posBufferRaw)
                else:
                    self.l_returnRaw.extend(self._posBuffer)
                    
        #>>> Make our stuff ====================================================================================
        if self._posBuffer: # Make our stuff
            mc.select(cl=1)
            #            if self._createMode and 

            #Delete the old stuff
            if self._createModeBuffer and not self.b_dragStoreMode:
                for o in self._createModeBuffer:
                    try:mc.delete(o)
                    except:pass
                self._createModeBuffer = []
                
            for i,pos in enumerate(self._posBuffer):
                for i2,v in enumerate(self.v_clampValues):
                    if v is not None:
                        pos[i2] = v
                        
                #Find our mesh...
                _rawPos = self._posBufferRaw[i]
                _m = False
                if _rawPos:
                    for i,m in enumerate(self.d_meshPos.keys()):
                        log.debug("|{0}|...mesh: {1}".format(_str_funcName,m))                                    
                        for i2,h in enumerate(self.d_meshPos[m]):
                            if h == _rawPos: 
                                log.debug("Found mesh match!")
                                _m = m
                                break
                else:
                    log.debug("no raw pos match")
                        
                #Let's make our stuff
                #baseScale = distance.returnMayaSpaceFromWorldSpace(10)
                if self._l_toDuplicate:
                    nameBuffer = []
                    for o in self._l_toDuplicate:
                        _dup = mc.duplicate(o)[0]
                        
                        _pos = pos 
                        
                        if self.str_offsetMode == 'snapCast':
                            try:
                                log.debug("snapCast: {0}".format(_dup))
                                
                                _pos_obj = POS.get(_dup,pivot='rp',space='w')#...Get the point of the object to snap
                                log.debug("startPoint: {0}".format(_pos_obj))
                                log.debug("posBuffer: {0}".format(_pos_base))
                                
                                _vec_obj = MATHUTILS.get_vector_of_two_points( _pos_obj,_pos_base)#...Get the vector from there to our hit
                                _dist_base = DIST.get_distance_between_points(_pos_base, _pos_obj)#...get our base distance
                                
                                _cast = RayCast.cast(self.l_mesh, startPoint=_pos_obj,vector=_vec_obj)
                                _nearHit = _cast['near']
                                _dist_firstHit = DIST.get_distance_between_points(_pos_obj,_nearHit)
                                log.debug("baseDist: {0}".format(_dist_base))
                                log.debug("firstHit: {0}".format(_dist_firstHit))
                                
                                if self.mode == 'far':
                                    _dist_new = _dist_base + _dist_firstHit
                                else:
                                    _dist_new = _dist_base - _dist_firstHit
                                _offsetPos = DIST.get_pos_by_vec_dist(_pos_obj,_vec_obj,(_dist_new))
                                
                                _pos = _offsetPos
                                
                                #Failsafe for casting to self...
                                if DIST.get_distance_between_points(_pos, _pos_obj) < _dist_firstHit:
                                    log.warning("Close proximity cast, using default")
                                    #_pos = self._posBuffer[-1]
                                    _pos = pos
                            except Exception,err:
                                _pos = _pos_base                         
                                log.error("SnapCast fail. Using original pos... | err: {0}".format(err))
                        try:
                            POS.set(_dup,_pos)
                        except Exception,err:
                            log.error("{0} failed to snap. err: {1}".format(o,err))   
                        if _m:
                            constBuffer = mc.normalConstraint(_m,_dup,
                                                              aimVector=[0,0,1],
                                                              upVector=[0,1,0],
                                                              worldUpType = 'scene')
                            mc.delete(constBuffer) 
                        nameBuffer.append(_dup)
                            
                else:
                    if self._createMode == 'joint':
                        nameBuffer = mc.joint(radius = 1)
                        #attributes.doSetAttr(nameBuffer,'radius',1)
                        mc.select(cl=True)
                    
                    else:
                        nameBuffer = mc.spaceLocator()[0]
    
                    #mc.move (pos[0],pos[1],pos[2], nameBuffer)
                    POS.set(nameBuffer,pos)
                    if _m:
                        constBuffer = mc.normalConstraint(_m,nameBuffer,
                                                          aimVector=[0,0,1],
                                                          upVector=[0,1,0],
                                                          worldUpType = 'scene')
                        mc.delete(constBuffer)
                        
                    #if self.l_toCreate:#Name it
                        #nameBuffer = mc.rename(nameBuffer,self.l_toCreate[len(self.l_return)])
                    nameBuffer = [nameBuffer]
    
                self._createModeBuffer.extend(nameBuffer)                        
                """
                for m in self.d_meshPos.keys():#check each mesh dictionary to see where it came from
                    if pos in self.d_meshPos[m]:#if the mesh has a match
                        attributes.storeInfo(nameBuffer,'cgmHitTarget',m)

                        #attributes.doSetAttr(nameBuffer,'localScaleX',(self.f_meshArea*.025))
                        #attributes.doSetAttr(nameBuffer,'localScaleY',(self.f_meshArea*.025))
                        #attributes.doSetAttr(nameBuffer,'localScaleZ',(self.f_meshArea*.025))

                        if self.v_posOffset is not None and self.v_posOffset and nameBuffer and self.str_offsetMode and self._createMode not in ['follicle']:
                            mi_obj = cgmMeta.cgmObject(nameBuffer)
                            mc.move (pos[0],pos[1],pos[2], mi_obj.mNode,ws=True)	
                            if self.str_offsetMode =='vector':
                                mi_hitLoc = cgmMeta.cgmObject(mc.spaceLocator(n='hitLoc')[0])
                                mc.move (self.startPoint[0],self.startPoint[1],self.startPoint[2], mi_hitLoc.mNode,ws=True)				
                                constBuffer = mc.aimConstraint(mi_hitLoc.mNode,mi_obj.mNode,
                                                               aimVector=[0,0,1],
                                                               upVector=[0,1,0],
                                                               worldUpType = 'scene')
                                mi_hitLoc.delete()
                            else:
                                constBuffer = mc.normalConstraint(m,mi_obj.mNode,
                                                                  aimVector=[0,0,1],
                                                                  upVector=[0,1,0],
                                                                  worldUpType = 'scene')
                            try:mc.delete(constBuffer)
                            except:pass
                            try:mc.move(self.v_posOffset[0],self.v_posOffset[1],self.v_posOffset[2], [mi_obj.mNode], r=True, rpr = True, os = True, wd = True)
                            except StandardError,error:log.error("%s >>> Failed to move! | self.v_posOffset: %s | mi_obj: %s | error: %s"%(_str_funcName,self.v_posOffset,mi_obj,error))				
                            self._posBuffer[i] = mi_obj.getPosition()  
                            if not self.b_orientSnap:
                                mi_obj.rotate = [0,0,0]
                        break                              

                        """
                

    
                

                    
            #if self._createModeBuffer:
                #self.l_created.extend(self._createModeBuffer)                
        mc.refresh()#Update maya to make it interactive!


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Functions
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def screenToWorld(startX,startY):
    """
    Function to convert a screen space draggerContext click to world space. 

    Arguments
    startX(int)
    startY(int)

    returns posDouble, vectorDouble
    """
    maya3DViewHandle = OpenMayaUI.M3dView() #3dView handle to be able to query
    activeView = maya3DViewHandle.active3dView() # Get the active view
    posMPoint = om.MPoint() #Storage items
    vecMVector = om.MVector()

    success = activeView.viewToWorld(startX, startY, posMPoint, vecMVector ) # The function

    return [posMPoint.x,posMPoint.y,posMPoint.z],[vecMVector.x,vecMVector.y,vecMVector.z]
