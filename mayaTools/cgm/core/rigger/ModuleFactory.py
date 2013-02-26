import copy
import re

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
from cgm.lib import (modules,curves,distance,attributes)
reload(attributes)
from cgm.lib.classes import NameFactory
from cgm.core.classes import DraggerContextFactory as dragFactory
reload(dragFactory)
from cgm.core.rigger import TemplateFactory as tFactory
reload(tFactory)
from cgm.core.rigger import JointFactory as jFactory
reload(jFactory)


##>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Shared libraries
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 
l_moduleStates = ['define','size','template','skeleton','rig']
l_modulesClasses = ['cgmModule','cgmLimb']
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Modules
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 
@r9General.Timer   
def isSized(self):
    """
    Return if a moudle is sized or not
    """
    log.debug(">>> isSized")    
    handles = self.templateNull.handles
    if len(self.coreNames.value) != handles:
        log.warning("Not enough names for handles")
        return False
    
    if self.templateNull.templateStarterData:
        if len(self.templateNull.templateStarterData) == handles:
            for i,pos in enumerate(self.templateNull.templateStarterData):
                if not pos:
                    log.warning("[%s] has no data"%(i))                    
                    return False
            return True
        else:
            log.warning("%i is not == %i handles necessary"%(len(self.templateNull.templateStarterData),handles))
            return False
    else:
        log.warning("No template starter data found for '%s'"%self.getShortName())  
    return False
    
    
def doSize(self,sizeMode='normal',geo = [],posList = [],*args,**kws):
    """
    Size a module
    1) Determine what points we need to gather
    2) Initiate draggerContextFactory
    3) Prompt user per point
    4) at the end of the day have a pos list the length of the handle list
    
    @ sizeMode
    'all' - pick every handle position
    'normal' - first/last, if child, will use last position of parent as first
    'manual' - provide a pos list to size from
    
    TODO:
    Add option for other modes
    Add geo argument that can be passed for speed
    Add clamp on value
    """
    log.debug(">>> doSize")    
    
    clickMode = {"heel":"surface"}    
    
    #Gather info
    #==============      
    handles = self.templateNull.handles
    if len(self.coreNames.value) == handles:
        names = self.coreNames.value
    else:
        log.warning("Not enough names. Generating")
        names = getGeneratedCoreNames(self)
    
    if not geo:
        geo = self.modulePuppet.getGeo()
    log.debug("Handles: %s"%handles)
    log.debug("Names: %s"%names)
    log.debug("Puppet: %s"%self.getMessage('modulePuppet'))
    log.debug("Geo: %s"%geo)
    log.debug("sizeMode: %s"%sizeMode)
    
    i_module = self #Bridge holder for our module class to go into our sizer class
    
    #Variables
    #============== 
    if sizeMode == 'manual':#To allow for a pos list to be input
        if not posList:
            log.error("Must have posList arg with 'manual' sizeMode!")
            return False
        
        if len(posList) < handles:
            log.warning("Creating curve to get enough points")                
            curve = curves.curveFromPosList(posList)
            mc.rebuildCurve (curve, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0,s=(handles-1), d=1, tol=0.001)
            posList = curves.returnCVsPosList(curve)#Get the pos of the cv's
            mc.delete(curve) 
            
        self.templateNull.__setattr__('templateStarterData',posList,lock=True)
        log.info("'%s' manually sized!"%self.getShortName())
        return True
            
    elif sizeMode == 'normal':
        if names > 1:
            namesToCreate = names[0],names[-1]
        else:
            namesToCreate = names
        log.info("Names: %s"%names)
    else:
        namesToCreate = names        
        sizeMode = 'all'
       
    class moduleSizer(dragFactory.clickMesh):
        """Sublass to get the functs we need in there"""
        def __init__(self,i_module = i_module,**kws):
            log.debug(">>> moduleSizer.__init__")    
            if kws:log.debug("kws: %s"%str(kws))
            
            super(moduleSizer, self).__init__(**kws)
            self.i_module = i_module
            log.info("Please place '%s'"%self.toCreate[0])
            
        def release(self):
            if len(self.returnList)< len(self.toCreate)-1:#If we have a prompt left
                log.info("Please place '%s'"%self.toCreate[len(self.returnList)+1])            
            dragFactory.clickMesh.release(self)

            
        def finalize(self):
            log.debug("returnList: %s"% self.returnList)
            log.debug("createdList: %s"% self.createdList)   
            buffer = [] #self.i_module.templateNull.templateStarterData
            log.debug("starting data: %s"% buffer)
            
            #Make sure we have enough points
            #==============  
            handles = self.i_module.templateNull.handles
            if len(self.returnList) < handles:
                log.warning("Creating curve to get enough points")                
                curve = curves.curveFromPosList(self.returnList)
                mc.rebuildCurve (curve, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0,s=(handles-1), d=1, tol=0.001)
                self.returnList = curves.returnCVsPosList(curve)#Get the pos of the cv's
                mc.delete(curve)

            #Store info
            #==============                  
            for i,p in enumerate(self.returnList):
                buffer.append(p)#need to ensure it's storing properly
                #log.info('[%s,%s]'%(buffer[i],p))
                
            #Store locs
            #==============  
            log.debug("finish data: %s"% buffer)
            self.templateNull.__setattr__('templateStarterData',buffer,lock=True)
            #self.i_module.templateNull.templateStarterData = buffer#store it
            log.info("'%s' sized!"%self.i_module.getShortName())
            dragFactory.clickMesh.finalize(self)
        
    #Start up our sizer    
    return moduleSizer(mode = 'midPoint',
                       mesh = geo,
                       create = 'locator',
                       toCreate = namesToCreate)
    
@r9General.Timer   
def doSetParentModule(self,moduleParent,force = False):
    """
    Set a module parent of a module

    module(string)
    """
    #See if parent exists and is a module, if so...
    #>>>buffer children
    #>>>see if already connected
    #>>Check existance
        #==============	
    #Get our instance
    log.debug(">>> doSetParentModule")
    
    try:
        moduleParent.mNode#See if we have an instance

    except:
        if mc.objExists(moduleParent):
            moduleParent = r9Meta.MetaClass(moduleParent)#initialize
        else:
            log.warning("'%s' doesn't exist"%moduleParent)#if it doesn't initialize, nothing is there		
            return False	

    #Logic checks
    #==============
    if not moduleParent.hasAttr('mClass'):
        log.warning("'%s' lacks an mClass attr"%module.mNode)	    
        return False

    if moduleParent.mClass not in ['cgmModule','cgmLimb']:
        log.warning("'%s' is not a recognized module type"%moduleParent.mClass)
        return False

    if not moduleParent.hasAttr('moduleChildren'):#Quick check
        log.warning("'%s'doesn't have 'moduleChildren' attr"%moduleParent.getShortName())#if it doesn't initialize, nothing is there		
        return False	

    buffer = copy.copy(moduleParent.getMessage('moduleChildren')) or []#Buffer till we have have append functionality	

    if self.mNode in buffer:
        log.warning("'%s' already connnected to '%s'"%(self.mNode,moduleParent.getShortName()))
        return False

        #Connect
        #==============	
    else:
        log.debug("Current children: %s"%moduleParent.getMessage('moduleChildren'))
        log.debug("Adding '%s'!"%self.getShortName())    

        buffer.append(self.mNode) #Revist when children has proper add/remove handling
        moduleParent.moduleChildren = buffer
        self.moduleParent = moduleParent.mNode
        #if moduleParent.getMessage('modulePuppet'):
            #moduleParent.modulePuppet.connectModule(self.mNode) 
            
        #del moduleParent.moduleChildren #Revist when children has proper add/remove handling
        #moduleParent.connectChildren(buffer,'moduleChildren','moduleParent',force=force)#Connect
        #if moduleParent.getMessage('modulePuppet'):
            #moduleParent.modulePuppet[0].connectModule(self)
            ##self.__setMessageAttr__('modulePuppet',moduleParent.getMessage('modulePuppet')[0])#Connect puppet to 

    self.parent = moduleParent.parent
    return True


@r9General.Timer   
def getGeneratedCoreNames(self):
    """ 
    Generate core names for a module and return them

    self MUST be cgmModule

    RETURNS:
    generatedNames(list)
    
    TODO:
    Where to store names?
    """
    log.debug(">>> getGeneratedCoreNames")    
    log.debug("Generating core names via ModuleFactory - '%s'"%self.getShortName())

    ### check the settings first ###
    partType = self.moduleType
    log.debug("%s partType is %s"%(self.getShortName(),partType))
    settingsCoreNames = modules.returncgmTemplateCoreNames(partType)
    handles = self.templateNull.handles
    partName = NameFactory.returnRawGeneratedName(self.mNode,ignore=['cgmType','cgmTypeModifier'])

    ### if there are no names settings, genearate them from name of the limb module###
    generatedNames = []
    if settingsCoreNames == False:   
        cnt = 1
        for handle in range(handles):
            generatedNames.append('%s%s%i' % (partName,'_',cnt))
            cnt+=1

    elif int(self.templateNull.handles) > (len(settingsCoreNames)):
        log.debug(" We need to make sure that there are enough core names for handles")       
        cntNeeded = self.templateNull.handles  - len(settingsCoreNames) +1
        nonSplitEnd = settingsCoreNames[len(settingsCoreNames)-2:]
        toIterate = settingsCoreNames[1]
        iterated = []
        for i in range(cntNeeded):
            iterated.append('%s%s%i' % (toIterate,'_',(i+1)))
        generatedNames.append(settingsCoreNames[0])
        for name in iterated:
            generatedNames.append(name)
        for name in nonSplitEnd:
            generatedNames.append(name) 

    else:
        generatedNames = settingsCoreNames[:self.templateNull.handles]

    #figure out what to do with the names
    self.coreNames.value = generatedNames
    """
    if not self.templateNull.templateStarterData:
        buffer = []
        for n in generatedNames:
            buffer.append([str(n),[]])
        self.templateNull.templateStarterData = buffer
    else:
        for i,pair in enumerate(self.templateNull.templateStarterData):
            pair[0] = generatedNames[i]    
    """
        
    return generatedNames

#=====================================================================================================
#>>> Template
#=====================================================================================================
@r9General.Timer   
def isTemplated(self):
    """
    Return if a module is templated or not
    """
    log.debug(">>> isTemplated")
    coreNamesValue = self.coreNames.value
    if not coreNamesValue:
        log.warning("No core names found")
        return False
    if not self.templateNull.getChildren():
        log.warning("No children found in template null")
        return False   
    
    for attr in 'controlObjects','root','curve','orientHelpers','orientRootHelper':
        if not self.templateNull.getMessage(attr):
            log.warning("No data found on '%s'"%attr)
            return False    
        
    if len(coreNamesValue) != len(self.templateNull.getMessage('controlObjects')):
        log.warning("Not enough handles.")
        return False    
        
    for i_obj in self.templateNull.controlObjects:#check for helpers
        if not i_obj.getMessage('helper'):
            log.warning("'%s' missing it's helper"%i_obj.getShortName())
            return False
    
    #self.moduleStates['templateState'] = True #Not working yet
    return True

@r9General.Timer   
def doTemplate(self,*args,**kws):
    try:
        if not isSized(self):
            log.warning("Not sized: '%s'"%self.getShortName())
            return False      
        tFactory.go(self)      
        if not isTemplated(self):
            log.warning("Template failed: '%s'"%self.getShortName())
            return False
        return True
    except StandardError,error:
        log.warning(error)    
    
@r9General.Timer   
def deleteTemplate(self,*args,**kws):
    try:
        objList = returnTemplateObjects(self)
        if objList:
            mc.delete(objList)
        return True
    except StandardError,error:
        log.warning(error)
@r9General.Timer   
def returnTemplateObjects(self):
    try:
        templateNull = self.templateNull.getShortName()
        returnList = []
        for obj in mc.ls(type = 'transform'):
            if attributes.doGetAttr(obj,'templateOwner') == templateNull:
                returnList.append(obj)
        return returnList
    except StandardError,error:
        log.warning(error)        
#=====================================================================================================
#>>> Skeleton
#=====================================================================================================
@r9General.Timer   
def isSkeletonized(self):
    """
    Return if a module is skeletonized or not
    """
    log.debug(">>> isSkeletonized")
    if not isTemplated(self):
        log.warning("Not templated, can't be skeletonized yet")
        return False
    
    l_coreNames = self.coreNames.value
    if not l_coreNames:
        log.warning("No core names found")
        return False
    
    iList_skinJoints = self.rigNull.skinJoints
    if not iList_skinJoints:
        log.warning("No skin joints found")
        return False        
    #>>> How many joints should we have 
    return True

@r9General.Timer   
def doSkeletonize(self,*args,**kws):
    try:
        if not isTemplated(self):
            log.warning("Not templated: '%s'"%self.getShortName())
            return False      
        jFactory.go(self)      
        if not isSkeletonized(self):
            log.warning("Skeleton build failed: '%s'"%self.getShortName())
            return False
        return True
    except StandardError,error:
        log.warning(error) 
        
@r9General.Timer   
def deleteSkeleton(self,*args,**kws):  
    log.info("deleteSkeleton: Not implemented")
    return True
#=====================================================================================================
#>>> States
#=====================================================================================================        
@r9General.Timer   
def isModule(self):
    """
    Simple module check
    """
    if not self.hasAttr('mClass'):
        log.warning("Has no 'mClass', not a module: '%s'"%self.getShortName())
        return False
    if self.mClass not in l_modulesClasses:
        log.warning("Class not a known module type: '%s'"%self.mClass)
        return False  
    log.debug("Is a module: : '%s'"%self.getShortName())
    return True

@r9General.Timer   
def getState(self):
    """ 
    Check module state ONLY from the state check attributes
    
    RETURNS:
    state(int) -- indexed to ModuleFactory.l_moduleStates
    
    Possible states:
    define
    sized
    templated
    skeletonized
    rigged
    """
    if not isModule(self):
        return False
    
    d_CheckList = {'size':isSized,
                   'template':isTemplated,
                   'skeleton':isSkeletonized
                   }
    goodState = 0
    for i,state in enumerate(l_moduleStates):
        if state in d_CheckList.keys():
            if d_CheckList[state](self):
                goodState = i
            else:break
        elif i != 0:
            log.warning("Need test for: '%s'"%state)
    log.info("'%s' state: %s | '%s'"%(self.getShortName(),goodState,l_moduleStates[goodState]))
    return goodState

@r9General.Timer   
def setState(self,stateArg,*args,**kws):
    """ 
    Set a module's state
    
    RETURNS:
    generatedNames(list)
    """
    d_upStateFunctions = {'size':doSize,
                           'template':doTemplate,
                           'skeleton':doSkeletonize
                           }
    d_downStateFunctions = {'size':deleteTemplate,
                           'template':deleteSkeleton
                           }
    if not isModule(self):
        return False
    
    #>>> Validate argument
    if type(stateArg) in [str,unicode]:
        if stateArg in l_moduleStates:
            stateIndex = l_moduleStates.index(stateArg)
            stateName = stateArg
        else:
            log.warning("Bad stateArg: %s"%stateArg)
            return False
    elif type(stateArg) is int:
        if stateArg<= len(l_moduleStates):
            stateIndex = stateArg
            stateName = l_moduleStates[stateArg]         
        else:
            log.warning("Bad stateArg: %s"%stateArg)
            return False        
    else:
        log.warning("Bad stateArg: %s"%stateArg)
        return False
    
    log.info("stateIndex: %s | stateName: '%s'"%(stateIndex,stateName))
    
    #>>> Meat
    #========================================================================
    currentState = getState(self) 
    if currentState == stateIndex:
        log.info("'%s' already has state: %s"%(self.getShortName(),stateName))
        return True
    #If we're here, we're going to move through the set states till we get to our spot
    if stateIndex > currentState:
        startState = currentState+1        
        log.debug(' up stating...')        
        log.debug("Starting doState: '%s'"%l_moduleStates[startState])
        doStates = l_moduleStates[startState:stateIndex+1]
        log.info("doStates: %s"%doStates)        
        for doState in doStates:
            if doState in d_upStateFunctions.keys():
                if not d_upStateFunctions[doState](self,*args,**kws):return False
                else:log.info("Comleted: %s"%doState)
            else:
                log.info("No up state function for: %s"%doState)
    else:#Going down
        log.debug('down stating...')        
        l_reverseModuleStates = copy.copy(l_moduleStates)
        l_reverseModuleStates.reverse()
        startState = currentState      
        log.debug(' up stating...')     
        log.debug("l_reverseModuleStates: %s"%l_reverseModuleStates)
        log.debug("Starting downState: '%s'"%l_moduleStates[startState])
        rev_start = l_reverseModuleStates.index( l_moduleStates[startState] )+1
        rev_end = l_reverseModuleStates.index( l_moduleStates[stateIndex] )+1
        doStates = l_reverseModuleStates[rev_start:rev_end]
        log.info("toDo: %s"%doStates)
        
        for doState in doStates:
            log.debug("doState: %s"%doState)
            if doState in d_downStateFunctions.keys():
                if not d_downStateFunctions[doState](self,*args,**kws):return False
                else:log.info("Comleted: %s"%doState)
            else:
                log.info("No down state function for: %s"%doState)            
    
    
