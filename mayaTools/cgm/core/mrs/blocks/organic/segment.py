"""
------------------------------------------
cgm.core.mrs.blocks.simple.torso
Author: Josh Burton
email: jjburton@cgmonks.com

Website : http://www.cgmonks.com
------------------------------------------

================================================================
"""
# From Python =============================================================
import copy
import re
import pprint
import time
import os

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc

# From Red9 =============================================================
from Red9.core import Red9_Meta as r9Meta
#r9Meta.cleanCache()#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< TEMP!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import cgm.core.cgm_General as cgmGEN

from cgm.core.rigger import ModuleShapeCaster as mShapeCast

import cgm.core.cgmPy.os_Utils as cgmOS
import cgm.core.cgmPy.path_Utils as cgmPATH
import cgm.core.mrs.assets as MRSASSETS
path_assets = cgmPATH.Path(MRSASSETS.__file__).up().asFriendly()

import cgm.core.mrs.lib.ModuleControlFactory as MODULECONTROL
reload(MODULECONTROL)
import cgm.core.lib.math_utils as MATH
import cgm.core.lib.transform_utils as TRANS
import cgm.core.lib.distance_utils as DIST
import cgm.core.lib.attribute_utils as ATTR
import cgm.core.tools.lib.snap_calls as SNAPCALLS
import cgm.core.classes.NodeFactory as NODEFACTORY
from cgm.core import cgm_RigMeta as cgmRigMeta
import cgm.core.lib.list_utils as LISTS
import cgm.core.lib.nameTools as NAMETOOLS

#Prerig handle making. refactor to blockUtils
import cgm.core.lib.snap_utils as SNAP
import cgm.core.lib.rayCaster as RAYS
import cgm.core.lib.rigging_utils as CORERIG
import cgm.core.lib.curve_Utils as CURVES
import cgm.core.rig.constraint_utils as RIGCONSTRAINT
reload(RIGCONSTRAINT)
import cgm.core.lib.constraint_utils as CONSTRAINT
import cgm.core.lib.position_utils as POS
import cgm.core.rig.joint_utils as JOINT
import cgm.core.rig.ik_utils as IK
import cgm.core.mrs.lib.block_utils as BLOCKUTILS
import cgm.core.cgm_RigMeta as cgmRIGMETA
import cgm.core.rig.skin_utils as CORESKIN
reload(CURVES)
#from cgm.core.lib import curve_Utils as CURVES
#import cgm.core.lib.rigging_utils as CORERIG
#from cgm.core.lib import snap_utils as SNAP
#import cgm.core.classes.NodeFactory as NODEFACTORY
#import cgm.core.lib.distance_utils as DIST
#import cgm.core.lib.position_utils as POS
#import cgm.core.rig.constraint_utils as RIGCONSTRAINT
#import cgm.core.lib.constraint_utils as CONSTRAINT
#import cgm.core.lib.locator_utils as LOC
#import cgm.core.lib.shape_utils as SHAPES
#import cgm.core.mrs.lib.block_utils as BLOCKUTILS
#import cgm.core.mrs.lib.builder_utils as BUILDERUTILS

#for m in DIST,POS,MATH,CONSTRAINT,LOC,BLOCKUTILS,BUILDERUTILS,CORERIG,RAYS,JOINT,RIGCONSTRAINT:
#    reload(m)
    
# From cgm ==============================================================
from cgm.core import cgm_Meta as cgmMeta

#=============================================================================================================
#>> Block Settings
#=============================================================================================================
__version__ = 'alpha.1.06012018'
__autoTemplate__ = False
__dimensions = [15.2, 23.2, 19.7]#...cm
__menuVisible__ = True
__sizeMode__ = 'castNames'

#__baseSize__ = 1,1,10

__l_rigBuildOrder__ = ['rig_dataBuffer',
                       'rig_skeleton',
                       'rig_shapes',
                       'rig_controls',
                       'rig_frame',
                       'rig_segments',
                       'rig_cleanUp']


d_wiring_skeleton = {'msgLists':['moduleJoints','skinJoints']}
d_wiring_prerig = {'msgLinks':['moduleTarget','prerigNull'],
                   'msgLists':['prerigHandles']}
d_wiring_template = {'msgLinks':['templateNull','prerigLoftMesh','orientHelper'],
                     'msgLists':['templateHandles']}

#>>>Profiles =====================================================================================================
d_build_profiles = {
    'unityLow':{'default':{'numJoints':3,
                           'numControls':3},
                   },
    'unityMed':{'default':{'numJoints':4,
                          'numControls':4},
               'spine':{'numJoints':4,
                       'numControls':4}},
    'unityHigh':{'default':{'numJoints':4,
                            'numControls':4},
                 'spine':{'numJoints':6,
                          'numControls':4}},
    
    'feature':{'default':{'numJoints':9,
                          'numControls':5}}}

d_block_profiles = {
    'tail':{'numShapers':5,
            'addCog':False,
            'cgmName':'tail',
            'loftShape':'wideDown',
            'loftSetup':'default',
            'ikSetup':'ribbon',
            'ikBase':'simple',
            'ikEnd':'tipBase',            
            'nameIter':'tail',
            'nameList':['tailBase','tailTip'],
            
            'squash':'both',
            'squashExtraControl':True,
            'squashMeasure':'pointDist',
            'squashFactorMax':1.0,
            'squashFactorMin':.25,
            'ribbonAim':'stableBlend',            

            'baseAim':[0,0,-1],
            'baseUp':[0,1,0],
            'baseSize':[2,8,2]},
    'fish':{'numShapers':5,
            'addCog':True,
            'cgmName':'fish',
            'loftShape':'circle',
            'loftSetup':'default',
            'ikSetup':'spline',
            'ikBase':'simple',
            'nameIter':'spine',
            'nameList':['head','tailFin'],
            'baseAim':[0,0,-1],
            'baseUp':[0,1,0],
            'baseSize':[2,8,2]},
    
    'spine':{'numShapers':8,
             'addCog':True,
             'loftSetup':'default',
             'loftShape':'square',
             'ikSetup':'ribbon',
             'ikBase':'hips',
             'ikEnd':'tipMid',             
             'cgmName':'spine',
             'nameIter':'spine',
             'nameList':['pelvis','chest'],
             
             'squash':'both',
             'squashExtraControl':True,
             'squashMeasure':'pointDist',
             'squashFactorMax':1.0,
             'squashFactorMin':0,
             'ribbonAim':'stable',
             
             'settingsPlace':'cog',
             'baseAim':[-90,0,0],
             'baseUp':[0,0,-1],
             'baseSize':[15,16,36]}}

#>>>Attrs =====================================================================================================
l_attrsStandard = ['side',
                   'position',
                   'baseUp',
                   'baseAim',
                   'addCog',
                   #'hasRootJoint',
                   'nameList',
                   'attachPoint',
                   'loftSides',
                   'loftDegree',
                   'loftSplit',
                   'loftShape',
                   'ikSetup',
                   'ikBase',
                   'nameIter',
                   'numControls',
                   'numShapers',
                   'numJoints',
                   #'buildProfile',
                   'numSpacePivots',
                   'scaleSetup',
                   'offsetMode',
                   'proxyDirect',
                   #'settingsPlace',
                   'settingsDirection',
                   'moduleTarget']

d_attrsToMake = {'proxyShape':'cube:sphere:cylinder',
                 'loftSetup':'default:torso',
                 
                 'squashMeasure' : 'none:arcLength:pointDist',
                 'squash' : 'none:simple:single:both',
                 'squashExtraControl' : 'bool',
                 'squashFactorMax':'float',
                 'squashFactorMin':'float',
                 
                 'ribbonAim': 'none:stable:stableBlend',
                 'ribbonConnectBy': 'constraint:matrix',
                 'segmentMidIKControl':'bool',
                 
                 'settingsPlace':'start:end:cog',
                 'blockProfile':':'.join(d_block_profiles.keys()),
                 'ikEnd':'none:cube:bank:foot:hand:tipBase:tipMid:tipEnd:proxy',
                 'spaceSwitch_direct':'bool',
                 #'nameIter':'string',
                 #'numControls':'int',
                 #'numShapers':'int',
                 #'numJoints':'int'
                 }

d_defaultSettings = {'version':__version__,
                     'baseSize':MATH.get_space_value(__dimensions[1]),
                     'numControls': 3,
                     'loftSetup':0,
                     'loftShape':0,
                     'numShapers':3,
                     
                     'squashMeasure':'arcLength',
                     'squash':'simple',
                     'squashFactorMax':1.0,
                     'squashFactorMin':0.0,
                     
                     'segmentMidIKControl':True,
                     'squash':'both',
                     'squashExtraControl':True,
                     'ribbonAim':'stableBlend',
                     
                     'settingsPlace':1,
                     'loftSides': 10,
                     'loftSplit':1,
                     'loftDegree':'cubic',
                     'numSpacePivots':2,
                     

                     
                     'ikBase':'cube',
                     'ikEnd':'cube',
                     
                     'numJoints':5,
                     'proxyDirect':True,
                     'spaceSwitch_direct':False,
                     'nameList':['',''],
                     #'blockProfile':'spine',
                     'attachPoint':'base',}



#Skeletal stuff ------------------------------------------------------------------------------------------------
d_skeletonSetup = {'mode':'curveCast',
                   'targetsMode':'prerigHandles',
                   'helperUp':'z-',
                   'countAttr':'neckJoints',
                   'targets':'jointHelper'}

#d_preferredAngles = {'head':[0,-10, 10]}#In terms of aim up out for orientation relative values, stored left, if right, it will invert
#d_rotationOrders = {'head':'yxz'}


#=================================================================================================
#>> Define
#================================================================================================
@cgmGEN.Timer
def define(self):
    _str_func = 'define'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug(self)
    
    _short = self.mNode
    ATTR.set_min(_short, 'numControls', 1)
    ATTR.set_min(_short, 'loftSides', 3)
    ATTR.set_min(_short, 'loftSplit', 1)
    ATTR.set_min(_short, 'numShapers', 2)
    self.doConnectOut('sy',['sx','sz'])    
    ATTR.set_alias(_short,'sy','blockScale')
    self.setAttrFlags(['sx','sz'])
    
    _blockScale = self.blockScale
    
    #Clean and data query ================================================================
    _shapes = self.getShapes()
    if _shapes:
        log.debug("|{0}| >>  Removing old shapes...".format(_str_func))        
        mc.delete(_shapes)
        defineNull = self.getMessage('defineNull')
        if defineNull:
            log.debug("|{0}| >>  Removing old defineNull...".format(_str_func))
            mc.delete(defineNull)
    
    _size = MATH.average(self.baseSize[1:])
    _crv = CURVES.create_fromName(name='axis3d',#'arrowsAxis', 
                                  direction = 'z+', size = _size/4)
    SNAP.go(_crv,self.mNode,)
    CORERIG.shapeParent_in_place(self.mNode,_crv,False)
    
    mHandleFactory = self.asHandleFactory()
    self.addAttr('cgmColorLock',True,lock=True,visible=False)
    #self.doStore('cgmNoRecolor',True)
    #self.setAttrFlags('cgmNoRecolor',lock=True,visible=False,keyable=False)
    
    mHandleFactory.color(self.mNode,controlType='main')
    #CORERIG.colorControl(self.mNode,_side,'main',transparent = True)
    
    mDefineNull = self.atUtils('stateNull_verify','define')
    
    #Aim Group ==================================================================
    mDefineNull.doConnectIn('rotate',"{0}.baseAim".format(_short))
    
    #Bounding box ==================================================================
    if self.getMessage('bbHelper'):
        self.bbHelper.delete()

    _bb_shape = CURVES.create_controlCurve(self.mNode,'cubeOpen', size = 1, sizeMode='fixed')
    _bb_newSize = MATH.list_mult(self.baseSize,[_blockScale,_blockScale,_blockScale])
    TRANS.scale_to_boundingBox(_bb_shape,_bb_newSize)
    mBBShape = cgmMeta.validateObjArg(_bb_shape, 'cgmObject',setClass=True)
    mBBShape.p_parent = mDefineNull

    mBBShape.inheritsTransform = False
    mc.parentConstraint(mDefineNull.mNode,mBBShape.mNode,maintainOffset=False)

    SNAPCALLS.snap( mBBShape.mNode,mDefineNull.mNode,objPivot='axisBox',objMode='z-')

    CORERIG.copy_pivot(mBBShape.mNode,self.mNode)
    self.doConnectOut('baseSize', "{0}.scale".format(mBBShape.mNode))
    mHandleFactory.color(mBBShape.mNode,controlType='sub')
    mBBShape.setAttrFlags()

    mBBShape.doStore('cgmName', self.mNode)
    mBBShape.doStore('cgmType','bbVisualize')
    mBBShape.doName()
    #mBBShape.template = True
    self.connectChildNode(mBBShape.mNode,'bbHelper')            
    
    
    #Up helper ==================================================================
    mTarget = self.doCreateAt()
    mTarget.p_parent = mDefineNull
    mTarget.rename('aimTarget')
    self.doConnectOut('baseSizeZ', "{0}.tz".format(mTarget.mNode))
    mTarget.setAttrFlags()
    
    _arrowUp = CURVES.create_fromName('pyramid', _size/5, direction= 'y+')
    mArrow = cgmMeta.validateObjArg(_arrowUp, 'cgmObject',setClass=True)
    mArrow.p_parent = mDefineNull    
    mArrow.resetAttrs()
    mHandleFactory.color(mArrow.mNode,controlType='sub')
    
    mArrow.doStore('cgmName', self.mNode)
    mArrow.doStore('cgmType','upVector')
    mArrow.doName()
    mArrow.setAttrFlags()
    
    
    #self.doConnectOut('baseSizeY', "{0}.ty".format(mArrow.mNode))
    NODEFACTORY.argsToNodes("{0}.ty = {1}.baseSizeY".format(mArrow.mNode,
                                                                self.mNode,
                                                                self.baseSize[1])).doBuild()
    
    mAimGroup = cgmMeta.validateObjArg(mArrow.doGroup(True,True,asMeta=True,typeModifier = 'aim'),'cgmObject',setClass=True)
    mAimGroup.resetAttrs()
    
    _const = mc.aimConstraint(mTarget.mNode, mAimGroup.mNode, maintainOffset = False,
                              aimVector = [0,0,1], upVector = [0,1,0], 
                              worldUpObject = mDefineNull.mNode,
                              worldUpType = 'objectrotation', 
                              worldUpVector = [0,1,0])
    cgmMeta.cgmNode(_const[0]).doConnectIn('worldUpVector','{0}.baseUp'.format(self.mNode))    
    mAimGroup.setAttrFlags()
    
    self.connectChildNode(mAimGroup.mNode,'rootUpHelper')
    
 
    #Plane helper ==================================================================
    plane = mc.nurbsPlane(axis = [1,0,0],#axis =  MATH.get_obj_vector(self.mNode, 'x+'),
                          width = 1, #height = 1,
                          #subdivisionsX=1,subdivisionsY=1,
                          ch=0)
    mPlane = cgmMeta.validateObjArg(plane[0])
    mPlane.doSnapTo(mDefineNull.mNode)
    mPlane.p_parent = mAimGroup
    mPlane.tz = .5
    CORERIG.copy_pivot(mPlane.mNode,self.mNode)

    self.doConnectOut('baseSize', "{0}.scale".format(mPlane.mNode))

    mHandleFactory.color(mPlane.mNode,controlType='sub')

    mPlane.doStore('cgmName', self.mNode)
    mPlane.doStore('cgmType','planeVisualize')
    mPlane.doName() 
    
    mPlane.setAttrFlags()
    
    
    """mAimGroup = mPlane.doGroup(True,True,asMeta=True,typeModifier = 'aim')
    mAimGroup.resetAttrs()
    
    mc.aimConstraint(mTarget.mNode, mAimGroup.mNode, maintainOffset = False,
                     aimVector = [0,0,1], upVector = [0,1,0], 
                     worldUpObject = self.rootUpHelper.mNode,
                     worldUpType = 'objectrotation', 
                     worldUpVector = [0,1,0])    """

 
    return    
    
    
#================================================================================================
#>> Template
#===============================================================================================  
@cgmGEN.Timer
def template(self):
    _str_func = 'template'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    self.defineNull.template = True
    

    #Initial checks ===============================================================================
    _short = self.p_nameShort
    _side = self.UTILS.get_side(self)
        
    _l_basePosRaw = self.datList_get('basePos') or [(0,0,0)]
    _l_basePos = [self.p_position]
    _baseUp = self.baseUp
    _baseSize = self.baseSize
    _baseAim = self.baseAim
    
    _ikSetup = self.getEnumValueString('ikSetup')
    _ikEnd = self.getEnumValueString('ikEnd')
    
    if MATH.is_vector_equivalent(_baseAim,_baseUp):
        raise ValueError,"baseAim and baseUp cannot be the same. baseAim: {0} | baseUp: {1}".format(self.baseAim,self.baseUp)
    
    _loftSetup = self.getEnumValueString('loftSetup')
            
    if _loftSetup not in ['default']:
        return log.error("|{0}| >> loft setup mode not done: {1}".format(_str_func,_loftSetup))
    

    
    #Get base dat =============================================================================    
    """#OLD METHOD...
    if not len(_l_basePos)>1:
        log.debug("|{0}| >> Generating more pos dat".format(_str_func))
        _end = DIST.get_pos_by_vec_dist(_l_basePos[0], _baseAim, max(_baseSize))
        _l_basePos.append(_end)
    
    _mVectorAim = MATH.get_vector_of_two_points(_l_basePos[0],_l_basePos[1],asEuclid=True)
    _mVectorUp = _mVectorAim.up()
    _worldUpVector = MATH.EUCLID.Vector3(self.baseUp[0],self.baseUp[1],self.baseUp[2])
    cgmGEN.func_snapShot(vars())"""
    
    _mVectorAim = MATH.get_obj_vector(self.bbHelper.mNode,asEuclid=True)
    mRootUpHelper = self.rootUpHelper
    _mVectorUp = MATH.get_obj_vector(mRootUpHelper.mNode,'y+',asEuclid=True)
    
    mBBHelper = self.bbHelper
    _v_range = max(TRANS.bbSize_get(self.mNode)) *2
    _bb_axisBox = SNAPCALLS.get_axisBox_size(mBBHelper.mNode, _v_range, mark=False)
    _size_width = _bb_axisBox[0]#...x width
    log.debug("|{0}| >> Generating more pos dat | bbHelper: {1} | range: {2}".format(_str_func,
                                                                                     mBBHelper.p_nameShort,
                                                                                     _v_range))
    _end = DIST.get_pos_by_vec_dist(_l_basePos[0], _mVectorAim, _bb_axisBox[2])
    _l_basePos.append(_end)
    
    #for i,p in enumerate(_l_basePos):
    #    LOC.create(position=p,name="{0}_loc".format(i))
    
    mBBHelper.v = False
    

    #Create temple Null  ==================================================================================
    mTemplateNull = self.UTILS.stateNull_verify(self,'template')
    mDefineNull = self.defineNull
    for a in ['translate','rotate','scale']:
        mDefineNull.doConnectOut(a,"{0}.{1}".format(mTemplateNull.mNode,a))
    mHandleFactory = self.asHandleFactory()
    
    #Handles ==================================================================================================
    log.debug("|{0}| >> handles...".format(_str_func)) 
    md_handles = {}
    ml_handles = []
    md_loftHandles = {}
    ml_loftHandles = []
    
    _loftShapeBase = self.getEnumValueString('loftShape')
    _loftShape = 'loft' + _loftShapeBase[0].capitalize() + ''.join(_loftShapeBase[1:])
    _loftSetup = self.getEnumValueString('loftSetup')
    
    
    if _loftSetup not in ['default']:
        return log.error("|{0}| >> loft setup mode not done: {1}".format(_str_func,_loftSetup))
    
    else:
        log.debug("|{0}| >> Default loft setup...".format(_str_func))         
        for i,n in enumerate(['start','end']):
            log.debug("|{0}| >> {1}:{2}...".format(_str_func,i,n)) 
            mHandle = mHandleFactory.buildBaseShape('sphere', _size_width, shapeDirection = 'y+')
            
            mHandle.p_parent = mTemplateNull
            
            self.copyAttrTo('cgmName',mHandle.mNode,'cgmName',driven='target')
            mHandle.doStore('cgmType','blockHandle')
            mHandle.doStore('cgmNameModifier',n)
            mHandle.doName()
            
            #Convert to loft curve setup ----------------------------------------------------
            mHandleFactory.setHandle(mHandle.mNode)
            #mHandleFactory = self.asHandleFactory(mHandle.mNode)
            mLoftCurve = mHandleFactory.rebuildAsLoftTarget(_loftShape, _size_width, shapeDirection = 'z+',rebuildHandle = False)
            
            mc.makeIdentity(mHandle.mNode,a=True, s = True)#...must freeze scale once we're back parented and positioned
            
            #mHandle.setAttrFlags(['rotate','tx'])
            #mc.transformLimits(mHandle.mNode,  tz = [-.25,.25], etz = [1,1], ty = [.1,1], ety = [1,0])
            #mTopLoftCurve = mHandle.loftCurve
            
            mHandleFactory.color(mHandle.mNode)
            #CORERIG.colorControl(mHandle.mNode,_side,'main',transparent = True)
            
            mHandle.p_position = _l_basePos[i]
            
            md_handles[n] = mHandle
            ml_handles.append(mHandle)
            
            md_loftHandles[n] = mLoftCurve                
            ml_loftHandles.append(mLoftCurve)
            
            mBaseAttachGroup = mHandle.doGroup(True, asMeta=True,typeModifier = 'attach')
            mBaseAimGroup = mHandle.doGroup(True, asMeta=True,typeModifier = 'aim')
            
            for mObj in mBaseAimGroup,mBaseAttachGroup:
                cgmMeta.validateObjArg(mObj,'cgmObject',setClass=True)
            
            
        #Aim the first and last joint with the root handle so the segment scales properly along line...
        mc.aimConstraint(md_handles['end'].attachGroup.mNode, md_handles['start'].aimGroup.mNode,
                         aimVector = [0,0,1], upVector = [0,1,0], 
                         worldUpObject = mRootUpHelper.mNode,
                         worldUpType = 'objectrotation',
                         worldUpVector = [0,1,0])
        
        mc.aimConstraint(md_handles['start'].attachGroup.mNode, md_handles['end'].aimGroup.mNode,
                         aimVector = [0,0,-1], upVector = [0,1,0], 
                         worldUpObject = mRootUpHelper.mNode,
                         worldUpType = 'objectrotation',
                         worldUpVector = [0,1,0])
        
        
        #>> Base Orient Helper =================================================================================
        mHandleFactory = self.asHandleFactory(md_handles['start'].mNode)
        mBaseOrientCurve = mHandleFactory.addOrientHelper(baseSize = _size_width,
                                                          shapeDirection = 'y+',
                                                          setAttrs = {'ty':_size_width})
        #'tz':- _size_width})
    
        self.copyAttrTo('cgmName',mBaseOrientCurve.mNode,'cgmName',driven='target')
        mBaseOrientCurve.doName()
        
        mBaseOrientCurve.p_parent =  mTemplateNull
        mOrientHelperAimGroup = mBaseOrientCurve.doGroup(True,asMeta=True,typeModifier = 'aim')        
        mc.pointConstraint(md_handles['start'].mNode, mOrientHelperAimGroup.mNode )
    
        _const = mc.aimConstraint(ml_handles[1].mNode, mOrientHelperAimGroup.mNode, maintainOffset = False,
                                  aimVector = [0,0,1], upVector = [0,1,0], 
                                  worldUpObject = mRootUpHelper.mNode,
                                  worldUpType = 'objectrotation',
                                  worldUpVector = [0,1,0])
        
        self.connectChildNode(mBaseOrientCurve.mNode,'orientHelper')
        #cgmMeta.cgmNode(_const[0]).doConnectIn('worldUpVector','{0}.baseUp'.format(self.mNode))
        #mBaseOrientCurve.p_parent = mStartAimGroup
        
        mBaseOrientCurve.setAttrFlags(['ry','rx','translate','scale','v'])
        mHandleFactory.color(mBaseOrientCurve.mNode,controlType='sub')
        mc.select(cl=True)
        
        
    
        #>>> Aim loft curves ===========================================================================        
        mStartLoft = md_loftHandles['start']
        mEndLoft = md_loftHandles['end']
        
        mStartAimGroup = mStartLoft.doGroup(True,asMeta=True,typeModifier = 'aim')
        mEndAimGroup = mEndLoft.doGroup(True,asMeta=True,typeModifier = 'aim')        
        
        #mc.aimConstraint(ml_handles[1].mNode, mStartAimGroup.mNode, maintainOffset = False,
        #                 aimVector = [0,1,0], upVector = [1,0,0], worldUpObject = ml_handles[0].mNode, #skip = 'z',
        #                 worldUpType = 'objectrotation', worldUpVector = [1,0,0])
        #mc.aimConstraint(ml_handles[0].mNode, mEndAimGroup.mNode, maintainOffset = False,
        #                 aimVector = [0,-1,0], upVector = [1,0,0], worldUpObject = ml_handles[-1].mNode,
        #                 worldUpType = 'objectrotation', worldUpVector = [1,0,0])             
        mc.aimConstraint(ml_handles[1].mNode, mStartAimGroup.mNode, maintainOffset = False,
                         aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = mBaseOrientCurve.mNode,
                         worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
        mc.aimConstraint(ml_handles[0].mNode, mEndAimGroup.mNode, maintainOffset = False,
                         aimVector = [0,0,-1], upVector = [0,1,0], worldUpObject = mBaseOrientCurve.mNode,
                         worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
        

        #Sub handles=========================================================================================
        if self.numShapers > 2:
            log.debug("|{0}| >> Sub handles..".format(_str_func))
            
            mNoTransformNull = self.UTILS.noTransformNull_verify(self,'template')
            
            mStartHandle = ml_handles[0]    
            mEndHandle = ml_handles[-1]    
            mOrientHelper = mStartHandle.orientHelper
        
            ml_handles = [mStartHandle]
            #ml_jointHandles = []        
        
            _size = MATH.average(mHandleFactory.get_axisBox_size(mStartHandle.mNode))
            #DIST.get_bb_size(mStartHandle.loftCurve.mNode,True)[0]
            _sizeSub = _size * .5    
            _vec_root_up = ml_handles[0].orientHelper.getAxisVector('y+')        
    

            _pos_start = mStartHandle.p_position
            _pos_end = mEndHandle.p_position 
            _vec = MATH.get_vector_of_two_points(_pos_start, _pos_end)
            _offsetDist = DIST.get_distance_between_points(_pos_start,_pos_end) / (self.numShapers - 1)
            _l_pos = [ DIST.get_pos_by_vec_dist(_pos_start, _vec, (_offsetDist * i)) for i in range(self.numShapers-1)] + [_pos_end]
        
            _mVectorAim = MATH.get_vector_of_two_points(_pos_start, _pos_end,asEuclid=True)
            _mVectorUp = _mVectorAim.up()
            _worldUpVector = [_mVectorUp.x,_mVectorUp.y,_mVectorUp.z]        
        
        
            #Linear track curve ----------------------------------------------------------------------
            _linearCurve = mc.curve(d=1,p=[_pos_start,_pos_end])
            mLinearCurve = cgmMeta.validateObjArg(_linearCurve,'cgmObject')
        
            l_clusters = []
            _l_clusterParents = [mStartHandle,mEndHandle]
            for i,cv in enumerate(mLinearCurve.getComponents('cv')):
                _res = mc.cluster(cv, n = 'test_{0}_{1}_cluster'.format(_l_clusterParents[i].p_nameBase,i))
                #_res = mc.cluster(cv)            
                #TRANS.parent_set( _res[1], _l_clusterParents[i].getMessage('loftCurve')[0])
                TRANS.parent_set(_res[1], mTemplateNull)
                mc.pointConstraint(_l_clusterParents[i].getMessage('loftCurve')[0],
                                   _res[1],maintainOffset=True)
                ATTR.set(_res[1],'v',False)                
                l_clusters.append(_res)
        
            pprint.pprint(l_clusters)
            
            mLinearCurve.parent = mNoTransformNull
            mLinearCurve.rename('template_trackCrv')
            
            #mLinearCurve.inheritsTransform = False      
        
        
            #Tmp loft mesh -------------------------------------------------------------------
            _l_targets = [mObj.loftCurve.mNode for mObj in [mStartHandle,mEndHandle]]
        
            _res_body = mc.loft(_l_targets, o = True, d = 3, po = 0 )
            _str_tmpMesh =_res_body[0]
        
            l_scales = []
        
            for mHandle in mStartHandle, mEndHandle:
                l_scales.append(mHandle.scale)
                mHandle.scale = 1,1,1

            #Sub handles... ------------------------------------------------------------------------------------
            for i,p in enumerate(_l_pos[1:-1]):
                #mHandle = mHandleFactory.buildBaseShape('circle', _size, shapeDirection = 'y+')
                mHandle = cgmMeta.cgmObject(name = 'handle_{0}'.format(i))
                _short = mHandle.mNode
                ml_handles.append(mHandle)
                mHandle.p_position = p
                SNAP.aim_atPoint(_short,_l_pos[i+2],'z+', 'y+', mode='vector', vectorUp = _vec_root_up)
        
                #...Make our curve
                _d = RAYS.cast(_str_tmpMesh, _short, 'y+')
                pprint.pprint(_d)
                log.debug("|{0}| >> Casting {1} ...".format(_str_func,_short))
                #cgmGEN.log_info_dict(_d,j)
                _v = _d['uvs'][_str_tmpMesh][0][0]
                log.debug("|{0}| >> v: {1} ...".format(_str_func,_v))
        
                #>>For each v value, make a new curve -----------------------------------------------------------------        
                #duplicateCurve -ch 1 -rn 0 -local 0  "loftedSurface2.u[0.724977270271534]"
                _crv = mc.duplicateCurve("{0}.u[{1}]".format(_str_tmpMesh,_v), ch = 0, rn = 0, local = 0)
                log.debug("|{0}| >> created: {1} ...".format(_str_func,_crv))  
        
                CORERIG.shapeParent_in_place(_short, _crv, False)
        
                #self.copyAttrTo(_baseNameAttrs[1],mHandle.mNode,'cgmName',driven='target')
                self.copyAttrTo('cgmName',mHandle.mNode,'cgmName',driven='target')
        
                mHandle.doStore('cgmType','blockHandle')
                mHandle.doStore('cgmIterator',i+1)
                mHandle.doName()
        
                mHandle.p_parent = mTemplateNull
        
                mGroup = mHandle.doGroup(True,True,asMeta=True,typeModifier = 'master')
                mGroup.p_parent = mTemplateNull
                
                _vList = DIST.get_normalizedWeightsByDistance(mGroup.mNode,[mStartHandle.mNode,mEndHandle.mNode])

                _scale = mc.scaleConstraint([mStartHandle.mNode,mEndHandle.mNode],mGroup.mNode,maintainOffset = False)#Point contraint loc to the object

                _res_attach = RIGCONSTRAINT.attach_toShape(mGroup.mNode, 
                                                           mLinearCurve.mNode,
                                                           'conPoint')
                TRANS.parent_set(_res_attach[0], mNoTransformNull.mNode)
                
                for c in [_scale]:
                    CONSTRAINT.set_weightsByDistance(c[0],_vList)
        
                #Convert to loft curve setup ----------------------------------------------------
                mHandleFactory = self.asHandleFactory(mHandle.mNode)
        
                mHandleFactory.rebuildAsLoftTarget('self', _size, shapeDirection = 'z+')

        
                CORERIG.colorControl(mHandle.mNode,_side,'sub',transparent = True)        
                #LOC.create(position = p)
        
            ml_handles.append(mEndHandle)
            mc.delete(_res_body)
        
            #Push scale back...
            for i,mHandle in enumerate([mStartHandle, mEndHandle]):
                mHandle.scale = l_scales[i]
        
            #Template Loft Mesh -------------------------------------
            #mTemplateLoft = self.getMessage('templateLoftMesh',asMeta=True)[0]        
            #for s in mTemplateLoft.getShapes(asMeta=True):
                #s.overrideDisplayType = 1       
            
            
            #Aim the segment
            for i,mHandle in enumerate(ml_handles):
                if mHandle != ml_handles[0] and mHandle != ml_handles[-1]:
                #if i > 0 and i < len(ml_handles) - 1:
                    mAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')

                    mc.aimConstraint(ml_handles[-1].mNode, mAimGroup.mNode, maintainOffset = True, #skip = 'z',
                                     aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = mBaseOrientCurve.mNode,
                                     worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
        
                                     
            mLoftCurve = mHandle.loftCurve
        
        
            #>>Loft Mesh ==================================================================================================
            targets = [mObj.loftCurve.mNode for mObj in ml_handles]        
        
            self.atUtils('create_prerigLoftMesh',
                         targets,
                         mTemplateNull,
                         'numControls',                     
                         'loftSplit',
                         polyType='bezier',
                         baseName = self.cgmName )
        
            """
                BLOCKUTILS.create_prerigLoftMesh(self,targets,
                                                 mPrerigNull,
                                                 'loftSplit',
                                                 'neckControls',
                                                 polyType='nurbs',
                                                 baseName = _l_baseNames[1] )     
                """
            for t in targets:
                ATTR.set(t,'v',0)                
            
            mNoTransformNull.v = False

        else:
            self.atUtils('create_templateLoftMesh',targets,self,
                         mTemplateNull,'numControls',
                         baseName = self.cgmName)            
        #>>> Connections ==========================================================================================
        self.msgList_connect('templateHandles',[mObj.mNode for mObj in ml_handles])

    #>>Loft Mesh ==================================================================================================
    targets = [mObj.mNode for mObj in ml_loftHandles]
    
    
    """
    BLOCKUTILS.create_templateLoftMesh(self,targets,mBaseLoftCurve,
                                       mTemplateNull,'numControls',
                                       baseName = _l_baseNames[1])"""


    #End setup======================================================================================
    if _ikSetup != 'none':
        mEndHandle = md_handles['end']
        log.debug("|{0}| >> ikSetup. End: {1}".format(_str_func,mEndHandle))
        mHandleFactory.setHandle(mEndHandle.mNode)
        
        if _ikEnd == 'bank':
            log.debug("|{0}| >> Bank setup".format(_str_func)) 
            mHandleFactory.addPivotSetupHelper().p_parent = mTemplateNull
        elif _ikEnd == 'foot':
            log.debug("|{0}| >> foot setup".format(_str_func)) 
            mFoot,mFootLoftTop = mHandleFactory.addFootHelper()
            mFoot.p_parent = mTemplateNull
        elif _ikEnd == 'proxy':
            log.debug("|{0}| >> proxy setup".format(_str_func)) 
            mProxy = mHandleFactory.addProxyHelper(shapeDirection = 'z+')
            mProxy.p_parent = mEndHandle
            
            pos_proxy = SNAPCALLS.get_special_pos(mEndHandle.p_nameLong,
                                                 'axisBox','z+',False)
            
            log.debug("|{0}| >> posProxy: {1}".format(_str_func,pos_proxy))
            mProxy.p_position = pos_proxy
            CORERIG.copy_pivot(mProxy.mNode,mEndHandle.mNode)
    
    self.blockState = 'template'#...buffer
    return True


#=============================================================================================================
#>> Prerig
#=============================================================================================================
def prerig(self):
    try:
        _str_func = 'prerig'
        _short = self.p_nameShort
        _side = self.atUtils('get_side')
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug(self)
        
        self.atUtils('module_verify')
        
        log.debug("|{0}| >> [{1}] | side: {2}".format(_str_func,_short, _side))   
        
        #Create some nulls Null  ==================================================================================
        mPrerigNull = self.atUtils('prerigNull_verify')
        #mNoTransformNull = self.atUtils('noTransformNull_verify')
        mNoTransformNull = self.UTILS.noTransformNull_verify(self,'prerig')
        
        #mNoTransformNull = BLOCKUTILS.noTransformNull_verify(self)
    
        #> Get our stored dat ==================================================================================================
        mHandleFactory = self.asHandleFactory()
        #mTemplateMesh = self.getMessage('templateLoftMesh',asMeta=True)[0]
        
        #Get positions
        #DIST.get_pos_by_axis_dist(obj, axis)
        
        ml_templateHandles = self.msgList_get('templateHandles')
        

        mStartHandle = ml_templateHandles[0]    
        mEndHandle = ml_templateHandles[-1]    
        mOrientHelper = mStartHandle.orientHelper
        
        ml_handles = []
       # ml_handles = [mStartHandle]        
        ml_jointHandles = []        
    
        _size = MATH.average(mHandleFactory.get_axisBox_size(mStartHandle.mNode))
        #DIST.get_bb_size(mStartHandle.loftCurve.mNode,True)[0]
        _sizeSub = _size * .33    
        _vec_root_up = ml_templateHandles[0].orientHelper.getAxisVector('y+')
        
        
        #Initial logic=========================================================================================
        log.debug("|{0}| >> Initial Logic...".format(_str_func)) 
        
        _pos_start = mStartHandle.p_position
        _pos_end = mEndHandle.p_position 
        _vec = MATH.get_vector_of_two_points(_pos_start, _pos_end)
        _offsetDist = DIST.get_distance_between_points(_pos_start,_pos_end) / (self.numControls - 1)
        
        _mVectorAim = MATH.get_vector_of_two_points(_pos_start, _pos_end,asEuclid=True)
        _mVectorUp = _mVectorAim.up()
        _worldUpVector = [_mVectorUp.x,_mVectorUp.y,_mVectorUp.z]        
    
    
        
        #Track curve ============================================================================
        log.debug("|{0}| >> TrackCrv...".format(_str_func)) 
        
        _trackCurve = mc.curve(d=1,p=[mObj.p_position for mObj in ml_templateHandles])
        mTrackCurve = cgmMeta.validateObjArg(_trackCurve,'cgmObject')
        mTrackCurve.rename(self.cgmName + 'prerigTrack_crv')
        mTrackCurve.parent = mNoTransformNull
        
        #mPrerigNull.connectChildNode('prerigTrackCurve',mTrackCurve.mNode,)
        
        l_clusters = []
        #_l_clusterParents = [mStartHandle,mEndHandle]
        for i,cv in enumerate(mTrackCurve.getComponents('cv')):
            _res = mc.cluster(cv, n = 'test_{0}_{1}_pre_cluster'.format(ml_templateHandles[i].p_nameBase,i))
            #_res = mc.cluster(cv)
            TRANS.parent_set( _res[1], ml_templateHandles[i].getMessage('loftCurve')[0])
            l_clusters.append(_res)
        
        pprint.pprint(l_clusters)
        
        
        """
        mTrackCurve.parent = mNoTransformNull
        #mLinearCurve.inheritsTransform = False
        ml_trackSkinJoints = []
        for mObj in ml_templateHandles:
            mJnt = mObj.loftCurve.doCreateAt('joint')
            mJnt.parent = mObj.loftCurve
            ml_trackSkinJoints.append(mJnt)
            
        mTrackCluster = cgmMeta.validateObjArg(mc.skinCluster ([mJnt.mNode for mJnt in ml_trackSkinJoints],
                                                               mTrackCurve.mNode,
                                                               tsb=True,
                                                               maximumInfluences = 1,
                                                               normalizeWeights = 1,dropoffRate=2.5),
                                              'cgmNode',
                                              setClass=True)
        
        mTrackCluster.doStore('cgmName', mTrackCurve.mNode)
        mTrackCluster.doName()    
            
            """
        l_scales = []
        for mHandle in ml_templateHandles:
            l_scales.append(mHandle.scale)
            mHandle.scale = 1,1,1
            
        _l_pos = CURVES.returnSplitCurveList(mTrackCurve.mNode,self.numControls,markPoints = False)
        #_l_pos = [ DIST.get_pos_by_vec_dist(_pos_start, _vec, (_offsetDist * i)) for i in range(self.numControls-1)] + [_pos_end]
            

        #Sub handles... ------------------------------------------------------------------------------------
        log.debug("|{0}| >> PreRig Handle creation...".format(_str_func))
        ml_aimGroups = []
        for i,p in enumerate(_l_pos):
            log.debug("|{0}| >> handle cnt: {1} | p: {2}".format(_str_func,i,p))
            crv = CURVES.create_fromName('cubeOpen', size = _sizeSub)
            mHandle = cgmMeta.validateObjArg(crv, 'cgmObject', setClass=True)
            #mHandle = cgmMeta.cgmObject(crv, name = 'handle_{0}'.format(i))
            _short = mHandle.mNode
            ml_handles.append(mHandle)
            mHandle.p_position = p
            """
            if p == _l_pos[-1]:
                SNAP.aim_atPoint(_short,_l_pos[-2],'z-', 'y+', mode='vector', vectorUp = _vec_root_up)
            else:
                SNAP.aim_atPoint(_short,_l_pos[i+1],'z+', 'y+', mode='vector', vectorUp = _vec_root_up)
            """
            mHandle.p_parent = mPrerigNull
            
            mGroup = mHandle.doGroup(True,True,asMeta=True,typeModifier = 'master')
            ml_aimGroups.append(mGroup)
            _vList = DIST.get_normalizedWeightsByDistance(mGroup.mNode,[mStartHandle.mNode,mEndHandle.mNode])
            #_point = mc.pointConstraint([mStartHandle.mNode,mEndHandle.mNode],mGroup.mNode,maintainOffset = True)#Point contraint loc to the object
            #_scale = mc.scaleConstraint([mStartHandle.mNode,mEndHandle.mNode],mGroup.mNode,maintainOffset = False)#Point contraint loc to the object
            #mLoc = mGroup.doLoc()
            #mLoc.parent = mNoTransformNull
            #mLoc.inheritsTransform = False
    
            _res_attach = RIGCONSTRAINT.attach_toShape(mGroup.mNode, mTrackCurve.mNode, 'conPoint')
            TRANS.parent_set(_res_attach[0], mNoTransformNull.mNode)
    
            #CURVES.attachObjToCurve(mLoc.mNode, mTrackCurve.mNode)
            #_point = mc.pointConstraint([mLoc.mNode],mGroup.mNode,maintainOffset = True)#Point contraint loc to the object
            
            #for c in [_scale]:
                #CONSTRAINT.set_weightsByDistance(c[0],_vList)
            
            mHandleFactory = self.asHandleFactory(mHandle.mNode)
            
            #Convert to loft curve setup ----------------------------------------------------
            ml_jointHandles.append(mHandleFactory.addJointHelper(baseSize = _sizeSub))
            #mRootCurve.setAttrFlags(['rotate','tx','tz'])
            #mc.transformLimits(mRootCurve.mNode,  tz = [-.25,.25], etz = [1,1], ty = [.1,1], ety = [1,0])
            #mTopLoftCurve = mRootCurve.loftCurve
            
            CORERIG.colorControl(mHandle.mNode,_side,'sub',transparent = True)        
            #LOC.create(position = p)
        
        #ml_handles.append(mEndHandle)
        self.msgList_connect('prerigHandles', ml_handles)
        
        ml_handles[0].connectChildNode(mOrientHelper.mNode,'orientHelper')      
        
        #mc.delete(_res_body)
        self.atUtils('prerigHandles_getNameDat',True)
        
        #Push scale back...
        for i,mHandle in enumerate(ml_templateHandles):
            mHandle.scale = l_scales[i]
        
        """
        #Template Loft Mesh -------------------------------------
        mTemplateLoft = self.getMessage('templateLoftMesh',asMeta=True)[0]        
        for s in mTemplateLoft.getShapes(asMeta=True):
            s.overrideDisplayType = 1       
        """
        
        #Aim the segment
        for i,mGroup in enumerate(ml_aimGroups):
            if mGroup == ml_aimGroups[-1]:
                SNAP.aim_atPoint(mGroup.mNode,_pos_start,'z-', 'y+', mode='vector', vectorUp = _worldUpVector)
            else:
                SNAP.aim_atPoint(mGroup.mNode,_pos_end,'z+', 'y+', mode='vector', vectorUp = _worldUpVector)            
        
        
        """
        #Aim the segment
        for i,mHandle in enumerate(ml_handles):
            #if i > 0 and i < len(ml_handles) - 1:
            mAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')
            
            if mHandle == ml_handles[-1]:
                pass
            else:
                mc.aimConstraint(ml_handles[i+1].mNode, mAimGroup.mNode, maintainOffset = True, #skip = 'z',
                                 aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = mOrientHelper.mNode,
                                 worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
                """
            
                    


        #>>Joint placers ====================================================================================    
        #Joint placer aim....
        
        for i,mHandle in enumerate(ml_handles):
            mJointHelper = mHandle.jointHelper
            mLoftCurve = mJointHelper.loftCurve
            
            if not mLoftCurve.getMessage('aimGroup'):
                mLoftCurve.doGroup(True,asMeta=True,typeModifier = 'aim')
                
            
            mAimGroup = mLoftCurve.getMessage('aimGroup',asMeta=True)[0]
        
            if mHandle == ml_handles[-1]:
                mc.aimConstraint(ml_handles[-2].mNode, mAimGroup.mNode, maintainOffset = False,
                                 aimVector = [0,0,-1], upVector = [0,1,0], worldUpObject = mOrientHelper.mNode, #skip = 'z',
                                 worldUpType = 'objectrotation', worldUpVector = [0,1,0])            
            else:
                mc.aimConstraint(ml_handles[i+1].mNode, mAimGroup.mNode, maintainOffset = False, #skip = 'z',
                                 aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = mOrientHelper.mNode,
                                 worldUpType = 'objectrotation', worldUpVector = [0,1,0])            
                                 
        #Joint placer loft....
        targets = [mObj.jointHelper.loftCurve.mNode for mObj in ml_handles]
        
        
        self.msgList_connect('jointHelpers',targets)
        
        self.atUtils('create_jointLoft',
                     targets,
                     mPrerigNull,
                     'numJoints',
                     baseName = self.cgmName )        
        
        """
        BLOCKUTILS.create_jointLoft(self,targets,
                                    mPrerigNull,'neckJoints',
                                    baseName = _l_baseNames[1] )
        """
        for t in targets:
            ATTR.set(t,'v',0)
            #ATTR.set_standardFlags(t,[v])
        
        
        #...cog -----------------------------------------------------------------------------
        if self.addCog:
            self.asHandleFactory(ml_templateHandles[0]).addCogHelper(shapeDirection='y+').p_parent = mPrerigNull        
        
        #Close out =============================================================================================
        mNoTransformNull.v = False
        cgmGEN.func_snapShot(vars())
        
        #if self.getMessage('templateLoftMesh'):
            #mTemplateLoft = self.getMessage('templateLoftMesh',asMeta=True)[0]
            #mTemplateLoft.v = False        
            
        return True
    
    except Exception,err:cgmGEN.cgmException(Exception,err)
    
def prerigDelete(self):
    if self.getMessage('templateLoftMesh'):
        mTemplateLoft = self.getMessage('templateLoftMesh',asMeta=True)[0]
        for s in mTemplateLoft.getShapes(asMeta=True):
            s.overrideDisplayType = 2
        mTemplateLoft.v = True


def skeleton_check(self):
    return True

def skeleton_build(self, forceNew = True):
    _short = self.mNode
    _str_func = 'skeleton_build'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    ml_joints = []
    
    mModule = self.moduleTarget
    if not mModule:
        raise ValueError,"No moduleTarget connected"
    mRigNull = mModule.rigNull
    if not mRigNull:
        raise ValueError,"No rigNull connected"
    
    ml_templateHandles = self.msgList_get('templateHandles',asMeta = True)
    if not ml_templateHandles:
        raise ValueError,"No templateHandles connected"
    
    ml_jointHelpers = self.msgList_get('jointHelpers',asMeta = True)
    if not ml_jointHelpers:
        raise ValueError,"No jointHelpers connected"
    
    #>> If skeletons there, delete ----------------------------------------------------------------------------------- 
    _bfr = mRigNull.msgList_get('moduleJoints',asMeta=True)
    if _bfr:
        log.debug("|{0}| >> Joints detected...".format(_str_func))            
        if forceNew:
            log.debug("|{0}| >> force new...".format(_str_func))                            
            mc.delete([mObj.mNode for mObj in _bfr])
        else:
            return _bfr
    
    #_baseNameAttrs = ATTR.datList_getAttrs(self.mNode,'baseNames')    

    log.debug("|{0}| >> creating...".format(_str_func))
    
    #_d = self.atBlockUtils('skeleton_getCreateDict', self.numJoints)
    
    if self.numJoints == self.numControls:
        log.debug("|{0}| >> Control count matches joint ({1})...".format(_str_func,self.numJoints))
        l_pos = []
        for mObj in ml_jointHelpers:
            l_pos.append(mObj.p_position)
    else:
        log.debug("|{0}| >> Generating count ({1})...".format(_str_func,self.numJoints))
        _crv = CURVES.create_fromList(targetList = [mObj.mNode for mObj in ml_jointHelpers])
        l_pos = CURVES.returnSplitCurveList(_crv,self.numJoints)
        mc.delete(_crv)        

    mOrientHelper = ml_templateHandles[0].orientHelper
    
    ml_joints = JOINT.build_chain(l_pos, parent=True, worldUpAxis= mOrientHelper.getAxisVector('y+'))
    
        
    _l_names = self.atUtils('skeleton_getNameDicts',True)

   
    for i,mJoint in enumerate(ml_joints):
        mJoint.rename(_l_names[i])
        

    ml_joints[0].parent = False
    
    _radius = DIST.get_distance_between_points(ml_joints[0].p_position, ml_joints[-1].p_position)/ 10
    #MATH.get_space_value(5)
    
    for mJoint in ml_joints:
        mJoint.displayLocalAxis = 1
        mJoint.radius = _radius

    mRigNull.msgList_connect('moduleJoints', ml_joints)
    
    #cgmGEN.func_snapShot(vars())    
    self.atBlockUtils('skeleton_connectToParent')
    
    return ml_joints


#=============================================================================================================
#>> rig
#=============================================================================================================
#NOTE - self here is a rig Factory....

#d_preferredAngles = {'default':[0,-10, 10]}#In terms of aim up out for orientation relative values, stored left, if right, it will invert
#d_preferredAngles = {'out':10}
d_preferredAngles = {}

d_rotateOrders = {'default':'yxz'}

#Rig build stuff goes through the rig build factory --------------------------------------------

@cgmGEN.Timer
def rig_prechecks(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_prechecks'
    log.debug("|{0}| >> ...".format(_str_func)+cgmGEN._str_hardBreak)
    log.debug(self)
    
    mBlock = self.mBlock    
    
    #Lever ============================================================================    
    _b_lever = False
    log.debug(cgmGEN._str_subLine)
    
    #if mBlock.scaleSetup:
        #self.l_precheckErrors.append('scaleSetup not ready')
        #return False        
        #raise NotImplementedError,"scaleSetup not ready."

@cgmGEN.Timer
def rig_dataBuffer(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_dataBuffer'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    mBlock = self.mBlock
    mModule = self.mModule
    mRigNull = self.mRigNull
    mPrerigNull = mBlock.prerigNull
    ml_templateHandles = mBlock.msgList_get('templateHandles')
    ml_handleJoints = mPrerigNull.msgList_get('handleJoints')
    mMasterNull = self.d_module['mMasterNull']
    
    self.mRootTemplateHandle = ml_templateHandles[0]
    
    #Initial option checks ============================================================================    
    #if mBlock.scaleSetup:
        #raise NotImplementedError,"Haven't setup scale yet."
    if mBlock.ikEnd in [2,3,4]:
        raise NotImplementedError,"Haven't setup ik end: {0}".format(ATTR.get_enumValueString(mBlock.mNode,'ikEnd'))
    #if mBlock.ikSetup > 1:
        #raise NotImplementedError,"Haven't setup ik mode: {0}".format(ATTR.get_enumValueString(mBlock.mNode,'ikSetup'))
    
    log.debug(cgmGEN._str_subLine)
        
    #Squash stretch logic  =================================================================================
    log.debug("|{0}| >> Squash stretch..".format(_str_func))
    self.b_scaleSetup = mBlock.scaleSetup
    
    self.b_squashSetup = False
    
    self.d_squashStretch = {}
    self.d_squashStretchIK = {}
    
    _squashStretch = None
    if mBlock.squash:
        _squashStretch =  mBlock.getEnumValueString('squash')
        self.b_squashSetup = True
    self.d_squashStretch['squashStretch'] = _squashStretch
    
    _squashMeasure = None
    if mBlock.squashMeasure:
        _squashMeasure =  mBlock.getEnumValueString('squashMeasure')    
    self.d_squashStretch['squashStretchMain'] = _squashMeasure    

    _driverSetup = None
    if mBlock.ribbonAim:
        _driverSetup =  mBlock.getEnumValueString('ribbonAim')
    self.d_squashStretch['driverSetup'] = _driverSetup

    
    self.d_squashStretch['extraSquashControl'] = mBlock.squashExtraControl
    self.d_squashStretch['squashFactorMax'] = mBlock.squashFactorMax
    self.d_squashStretch['squashFactorMin'] = mBlock.squashFactorMin
    
    log.debug("|{0}| >> self.d_squashStretch..".format(_str_func))    
    pprint.pprint(self.d_squashStretch)
    
    #Check for mid control and even handle count to see if w need an extra curve
    if mBlock.segmentMidIKControl:
        if MATH.is_even(mBlock.numControls):
            self.d_squashStretchIK['sectionSpans'] = 2
            
    if self.d_squashStretchIK:
        log.debug("|{0}| >> self.d_squashStretchIK..".format(_str_func))    
        pprint.pprint(self.d_squashStretchIK)
    
    
    if not self.b_scaleSetup:
        pass
    
    log.debug("|{0}| >> self.b_scaleSetup: {1}".format(_str_func,self.b_scaleSetup))
    log.debug("|{0}| >> self.b_squashSetup: {1}".format(_str_func,self.b_squashSetup))
    
    log.debug(cgmGEN._str_subLine)
    
    #Frame Handles =============================================================================
    self.mToe = False
    self.mBall = False
    self.int_handleEndIdx = -1
    self.b_ikNeedEnd = False
    l= []
    
    str_ikEnd = ATTR.get_enumValueString(mBlock.mNode,'ikEnd')
    log.debug("|{0}| >> IK End: {1}".format(_str_func,str_ikEnd))
    
    if str_ikEnd in ['foot','hand']:
        raise NotImplemented,"not done"
        if mBlock.hasEndJoint:
            self.mToe = self.ml_handleTargets.pop(-1)
            log.debug("|{0}| >> mToe: {1}".format(_str_func,self.mToe))
            self.int_handleEndIdx -=1
        if mBlock.hasBallJoint:
            self.mBall = self.ml_handleTargets.pop(-1)
            log.debug("|{0}| >> mBall: {1}".format(_str_func,self.mBall))        
            self.int_handleEndIdx -=1
    elif str_ikEnd in ['tipEnd','tipBase']:
        log.debug("|{0}| >> tip setup...".format(_str_func))        
        #if not mBlock.hasEndJoint:
            #self.b_ikNeedEnd = True
            #log.debug("|{0}| >> Need IK end joint".format(_str_func))
        #else:
        if str_ikEnd == 'tipBase':
            self.int_handleEndIdx -=1
            
    log.debug("|{0}| >> self.int_handleEndIdx: {1}".format(_str_func,self.int_handleEndIdx))
    
    
    
    str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')
    log.debug("|{0}| >> IK Base: {1}".format(_str_func,str_ikBase))    
    self.int_segBaseIdx = 0
    if str_ikBase in ['hips']:
        self.int_segBaseIdx = 1
    log.debug("|{0}| >> self.int_segBaseIdx: {1}".format(_str_func,self.int_segBaseIdx))
    
    
    log.debug(cgmGEN._str_subLine)
    
    #Offset ============================================================================    
    str_offsetMode = ATTR.get_enumValueString(mBlock.mNode,'offsetMode')
    if not mBlock.offsetMode:
        log.debug("|{0}| >> default offsetMode...".format(_str_func))
        self.v_offset = self.mPuppet.atUtils('get_shapeOffset')
    else:
        str_offsetMode = ATTR.get_enumValueString(mBlock.mNode,'offsetMode')
        log.debug("|{0}| >> offsetMode: {1}".format(_str_func,str_offsetMode))
        
        l_sizes = []
        for mHandle in ml_templateHandles:
            #_size_sub = SNAPCALLS.get_axisBox_size(mHandle)
            #l_sizes.append( MATH.average(_size_sub[1],_size_sub[2]) * .1 )
            _size_sub = POS.get_bb_size(mHandle,True)
            l_sizes.append( MATH.average(_size_sub) * .1 )            
        self.v_offset = MATH.average(l_sizes)
        #_size_midHandle = SNAPCALLS.get_axisBox_size(ml_templateHandles[self.int_handleMidIdx])
        #self.v_offset = MATH.average(_size_midHandle[1],_size_midHandle[2]) * .1        
    log.debug("|{0}| >> self.v_offset: {1}".format(_str_func,self.v_offset))    
    
    
    #DynParents =============================================================================
    reload(self.UTILS)
    self.UTILS.get_dynParentTargetsDat(self)

    #rotateOrder =============================================================================
    _str_orientation = self.d_orientation['str']
    self.rotateOrder = "{0}{1}{2}".format(_str_orientation[1],_str_orientation[2],_str_orientation[0])
    log.debug("|{0}| >> rotateOrder | self.rotateOrder: {1}".format(_str_func,self.rotateOrder))

    log.debug(cgmGEN._str_subLine)

    return True




@cgmGEN.Timer
def rig_skeleton(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_skeleton'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug(self)    
    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    ml_jointsToConnect = []
    ml_jointsToHide = []
    ml_blendJoints = []
    ml_joints = mRigNull.msgList_get('moduleJoints')
    self.d_joints['ml_moduleJoints'] = ml_joints
    
    str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')        
    
    reload(BLOCKUTILS)
    BLOCKUTILS.skeleton_pushSettings(ml_joints,self.d_orientation['str'],
                                     self.d_module['mirrorDirection'],
                                     d_rotateOrders)#, d_preferredAngles)
    
    
    log.debug("|{0}| >> rig chain...".format(_str_func))              
    ml_rigJoints = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock, ml_joints, 'rig', self.mRigNull,'rigJoints',blockNames=True)
    pprint.pprint(ml_rigJoints)
    
    #...fk chain -----------------------------------------------------------------------------------------------
    log.debug("|{0}| >> fk_chain".format(_str_func))
    ml_fkJoints = BLOCKUTILS.skeleton_buildHandleChain(mBlock,'fk','fkJoints')
    
    ml_jointsToHide.extend(ml_fkJoints)


    #...fk chain -----------------------------------------------------------------------------------------------
    if mBlock.ikSetup:
        log.debug("|{0}| >> ikSetup on. Building blend and IK chains...".format(_str_func))  
        ml_blendJoints = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'blend','blendJoints')
        ml_ikJoints = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'ik','ikJoints')
        ml_jointsToConnect.extend(ml_ikJoints)
        ml_jointsToHide.extend(ml_blendJoints)
        
        #BLOCKUTILS.skeleton_pushSettings(ml_ikJoints,self.d_orientation['str'],
        #                                 self.d_module['mirrorDirection'],
        #                                 d_rotateOrders, d_preferredAngles)
        
        for i,mJnt in enumerate(ml_ikJoints):
            if mJnt not in [ml_ikJoints[0],ml_ikJoints[-1]]:
                mJnt.preferredAngle = mJnt.jointOrient
                
        
        
    #cgmGEN.func_snapShot(vars())        
    """
    if mBlock.numControls > 1:
        log.debug("|{0}| >> Handles...".format(_str_func))            
        ml_segmentHandles = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'handle','handleJoints',clearType=True)
        if mBlock.ikSetup:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_blendJoints[i]
        else:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_fkJoints[i]
                """
    
    if mBlock.ikSetup in [2,3]:#...ribbon/spline
        log.debug("|{0}| >> IK Drivers...".format(_str_func))            
        ml_ribbonIKDrivers = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,ml_ikJoints, None, mRigNull,'ribbonIKDrivers', cgmType = 'ribbonIKDriver', indices=[0,-1])
        for i,mJnt in enumerate(ml_ribbonIKDrivers):
            mJnt.parent = False
            
            mTar = ml_blendJoints[0]
            if i == 0:
                mTar = ml_blendJoints[0]
            else:
                mTar = ml_blendJoints[-1]
                
            mJnt.doCopyNameTagsFromObject(mTar.mNode,ignore=['cgmType'])
            mJnt.doName()
        
        ml_jointsToConnect.extend(ml_ribbonIKDrivers)
        
        
        if mBlock.segmentMidIKControl:
            log.debug("|{0}| >> Creating ik mid control...".format(_str_func))  
            #Lever...
            mMidIK = ml_rigJoints[0].doDuplicate(po=True)
            mMidIK.cgmName = '{0}_segMid'.format(mBlock.cgmName)
            mMidIK.p_parent = False
            mMidIK.doName()
        
            mMidIK.p_position = DIST.get_average_position([ml_rigJoints[self.int_segBaseIdx].p_position,
                                                          ml_rigJoints[-1].p_position])
        
            SNAP.aim(mMidIK.mNode, ml_rigJoints[-1].mNode, 'z+','y+','vector',
                     mBlock.rootUpHelper.getAxisVector('y+'))
            reload(JOINT)
            JOINT.freezeOrientation(mMidIK.mNode)
            mRigNull.connectChildNode(mMidIK,'controlSegMidIK','rigNull')
        
    
    if mBlock.numJoints > mBlock.numControls or self.b_squashSetup:
        log.debug("|{0}| >> Handles...".format(_str_func))            
        ml_segmentHandles = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'handle','handleJoints',clearType=True)
        if mBlock.ikSetup:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_blendJoints[i]
        else:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_fkJoints[i]        
        
        
        log.debug("|{0}| >> segment necessary...".format(_str_func))
            
        ml_segmentChain = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,ml_joints, None, mRigNull,'segmentJoints', cgmType = 'segJnt',blockNames=True)
        for i,mJnt in enumerate(ml_rigJoints):
            mJnt.parent = ml_segmentChain[i]
            mJnt.connectChildNode(ml_segmentChain[i],'driverJoint','sourceJoint')#Connect
        ml_jointsToHide.extend(ml_segmentChain)
    else:
        log.debug("|{0}| >> Simple setup. Parenting rigJoints to blend...".format(_str_func))
        ml_rigParents = ml_fkJoints
        if ml_blendJoints:
            ml_rigParents = ml_blendJoints
        for i,mJnt in enumerate(ml_rigJoints):
            mJnt.parent = ml_blendJoints[i]
            
        if str_ikBase == 'hips':
            log.debug("|{0}| >> Simple setup. Need single handle.".format(_str_func))
            ml_segmentHandles = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,
                                                                        ml_fkJoints, 
                                                                        'handle', mRigNull,
                                                                        'handleJoints',
                                                                        cgmType = 'handle', indices=[1])
            
        
    #...joint hide -----------------------------------------------------------------------------------
    for mJnt in ml_jointsToHide:
        try:
            mJnt.drawStyle =2
        except:
            mJnt.radius = .00001
            
    #...connect... 
    self.fnc_connect_toRigGutsVis( ml_jointsToConnect )        
    #cgmGEN.func_snapShot(vars())     
    return True

@cgmGEN.Timer
def rig_shapes(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_shapes'
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug(self)
        
        mBlock = self.mBlock
        mRigNull = self.mRigNull
        
        ml_templateHandles = mBlock.msgList_get('templateHandles')
        ml_prerigHandleTargets = mBlock.atBlockUtils('prerig_getHandleTargets')
        ml_fkJoints = mRigNull.msgList_get('fkJoints')
        ml_ikJoints = mRigNull.msgList_get('ikJoints',asMeta=True)
        ml_blendJoints = mRigNull.msgList_get('blendJoints')
        
        mIKEnd = ml_prerigHandleTargets[-1]
        ml_prerigHandles = mBlock.msgList_get('prerigHandles')
        
        _side = mBlock.atUtils('get_side')
        _short_module = self.mModule.mNode
        str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')
        str_ikEnd = ATTR.get_enumValueString(mBlock.mNode,'ikEnd')
        
        mHandleFactory = mBlock.asHandleFactory()
        mOrientHelper = ml_prerigHandles[0].orientHelper
        
        #_size = 5
        #_size = MATH.average(mHandleFactory.get_axisBox_size(ml_prerigHandles[0].mNode))
        _jointOrientation = self.d_orientation['str']
        
        ml_joints = self.d_joints['ml_moduleJoints']
        
        #Our base size will be the average of the bounding box sans the largest
        _bbSize = TRANS.bbSize_get(mBlock.getMessage('prerigLoftMesh')[0],shapes=True)
        _bbSize.remove(max(_bbSize))
        _size = MATH.average(_bbSize)        
        _offset = self.v_offset
        mCog = False
        
        #Figure out our handle targets...
        ml_handleTargets = ml_fkJoints
        
        #controlSegMidIK =============================================================================
        if mRigNull.getMessage('controlSegMidIK'):
            log.debug("|{0}| >> controlSegMidIK...".format(_str_func))            
            mControlSegMidIK = mRigNull.getMessage('controlSegMidIK',asMeta=1)[0]
            
            ml_shapes = self.atBuilderUtils('shapes_fromCast',
                                            targets = mControlSegMidIK,
                                            offset = _offset,
                                            mode = 'simpleCast')#'segmentHan
            CORERIG.shapeParent_in_place(mControlSegMidIK.mNode, ml_shapes[0].mNode,False)
            
            mControlSegMidIK.doStore('cgmTypeModifier','ik')
            mControlSegMidIK.doStore('cgmType','handle')
            mControlSegMidIK.doName()            

            mHandleFactory.color(mControlSegMidIK.mNode, controlType = 'sub')
            
        
        #Cog =============================================================================
        if mBlock.getMessage('cogHelper') and mBlock.getMayaAttr('addCog'):
            log.debug("|{0}| >> Cog...".format(_str_func))
            mCogHelper = mBlock.cogHelper
            
            mCog = mCogHelper.shapeHelper.doCreateAt(setClass=True)
            CORERIG.shapeParent_in_place(mCog.mNode, mCogHelper.shapeHelper.mNode)
            
            mCog.doStore('cgmName','cog')
            mCog.doStore('cgmAlias','cog')            
            mCog.doName()
            
            mRigNull.connectChildNode(mCog,'rigRoot','rigNull')#Connect
            mRigNull.connectChildNode(mCog,'settings','rigNull')#Connect        
            
        
        else:#Root =============================================================================
            log.debug("|{0}| >> Root...".format(_str_func))
            
            mRootHandle = ml_prerigHandles[0]
            #mRoot = ml_joints[0].doCreateAt()
            mRoot = ml_joints[0].doCreateAt()
            
            _size_root =  MATH.average(mHandleFactory.get_axisBox_size(ml_templateHandles[0].mNode))
            mRootCrv = cgmMeta.validateObjArg(CURVES.create_fromName('sphere', _size_root * 1.5),'cgmObject',setClass=True)
            mRootCrv.doSnapTo(mRootHandle)
        
            #SNAP.go(mRootCrv.mNode, ml_joints[0].mNode,position=False)
        
            CORERIG.shapeParent_in_place(mRoot.mNode,mRootCrv.mNode, False)
        
            ATTR.copy_to(_short_module,'cgmName',mRoot.mNode,driven='target')
            mRoot.doStore('cgmTypeModifier','root')
            mRoot.doName()
            
            mHandleFactory.color(mRoot.mNode, controlType = 'sub')
            
            mRigNull.connectChildNode(mRoot,'rigRoot','rigNull')#Connect
        
        
        #Settings =============================================================================
        _settingsPlace = mBlock.getEnumValueString('settingsPlace')
        if _settingsPlace == 'cog':
            if mCog:
                log.debug("|{0}| >> Settings is cog...".format(_str_func))
                mRigNull.connectChildNode(mCog,'settings','rigNull')#Connect
            else:
                log.warning("|{0}| >> Settings. Cog option but no cog found...".format(_str_func))
                _settingsPlace = 'start'
        
        if _settingsPlace != 'cog':
            log.debug("|{0}| >> settings: {1}...".format(_str_func,_settingsPlace))
            
            if ml_blendJoints:
                ml_targets = ml_blendJoints
            else:
                ml_targets = ml_fkJoints
        
            if _settingsPlace == 'start':
                _mTar = ml_targets[0]
                _settingsSize = MATH.average(TRANS.bbSize_get(self.mRootTemplateHandle.mNode,shapes=True))
            else:
                _mTar = ml_targets[self.int_handleEndIdx]
                _settingsSize = MATH.average(TRANS.bbSize_get(ml_templateHandles[-1].mNode,shapes=True))
        
            mSettingsShape = cgmMeta.validateObjArg(CURVES.create_fromName('gear',_settingsSize * .5,
                                                                           '{0}+'.format(_jointOrientation[2])),'cgmObject',setClass=True)
        
            mSettingsShape.doSnapTo(_mTar.mNode)
            d_directions = {'up':'y+','down':'y-','in':'x+','out':'x-'}
            str_settingsDirections = d_directions.get(mBlock.getEnumValueString('settingsDirection'),'y+')
            mSettingsShape.p_position = _mTar.getPositionByAxisDistance(str_settingsDirections,
                                                                        _settingsSize)
        
            SNAP.aim_atPoint(mSettingsShape.mNode,
                             _mTar.p_position,
                             aimAxis=_jointOrientation[0]+'+',
                             mode = 'vector',
                             vectorUp= _mTar.getAxisVector(_jointOrientation[0]+'-'))
        
            mSettingsShape.parent = _mTar
            mSettings = mSettingsShape
            CORERIG.match_orientation(mSettings.mNode, _mTar.mNode)
        
            ATTR.copy_to(_short_module,'cgmName',mSettings.mNode,driven='target')
        
            mSettings.doStore('cgmTypeModifier','settings')
            mSettings.doName()
            mHandleFactory.color(mSettings.mNode, controlType = 'sub')
        
            mRigNull.connectChildNode(mSettings,'settings','rigNull')#Connect                    
            

        #Direct Controls =============================================================================
        log.debug("|{0}| >> direct...".format(_str_func))                
        ml_rigJoints = self.mRigNull.msgList_get('rigJoints')
        
        if len(ml_rigJoints) < 3:
            _size_direct = DIST.get_distance_between_targets([mObj.mNode for mObj in ml_rigJoints], average=True)        
            d_direct = {'size':_size_direct/2}
        else:
            d_direct = {'size':None}
            
        ml_directShapes = self.atBuilderUtils('shapes_fromCast',
                                              ml_rigJoints,
                                              mode ='direct',**d_direct)
                                                                                                                                                                #offset = 3
    
        for i,mCrv in enumerate(ml_directShapes):
            mHandleFactory.color(mCrv.mNode, controlType = 'sub')
            CORERIG.shapeParent_in_place(ml_rigJoints[i].mNode,mCrv.mNode, False, replaceShapes=True)
            #for mShape in ml_rigJoints[i].getShapes(asMeta=True):
                #mShape.doName()
    
        for mJnt in ml_rigJoints:
            try:
                mJnt.drawStyle =2
            except:
                mJnt.radius = .00001

        
        #Handles ===========================================================================================
        ml_handleJoints = self.mRigNull.msgList_get('handleJoints')
        
        if ml_handleJoints:
            log.debug("|{0}| >> Found Handle joints...".format(_str_func))
            #l_uValues = MATH.get_splitValueList(.01,.99, len(ml_handleJoints))
            ml_handleShapes = self.atBuilderUtils('shapes_fromCast',
                                                  targets = ml_handleJoints,
                                                  offset = _offset,
                                                  mode = 'limbSegmentHandle')#'segmentHandle') limbSegmentHandle
            """
            if str_ikBase == 'hips':
                mHandleFactory.color(ml_handleShapes[1].mNode, controlType = 'sub')            
                CORERIG.shapeParent_in_place(ml_handleJoints[0].mNode, 
                                             ml_handleShapes[1].mNode, False,
                                             replaceShapes=True)
                for mObj in ml_handleShapes:
                    try:mObj.delete()
                    except:pass"""
                
            for i,mCrv in enumerate(ml_handleShapes):
                log.debug("|{0}| >> Shape: {1} | Handle: {2}".format(_str_func,mCrv.mNode,ml_handleJoints[i].mNode ))                
                mHandleFactory.color(mCrv.mNode, controlType = 'sub')            
                CORERIG.shapeParent_in_place(ml_handleJoints[i].mNode, 
                                             mCrv.mNode, False,
                                             replaceShapes=True)
                #for mShape in ml_handleJoints[i].getShapes(asMeta=True):
                    #mShape.doName()
        
        
    
    
        #IK Shapes =============================================================================
        ml_fkShapes = self.atBuilderUtils('shapes_fromCast',
                                          targets = ml_fkJoints,
                                          offset = _offset,
                                          mode = 'frameHandle')
        
        #IK End ---------------------------------------------------------------------------------
        if mBlock.ikSetup:
            log.debug("|{0}| >> ikHandle...".format(_str_func))
            if ml_templateHandles[-1].getMessage('proxyHelper'):
                log.debug("|{0}| >> proxyHelper IK shape...".format(_str_func))
                mProxyHelper = ml_templateHandles[-1].getMessage('proxyHelper',asMeta=True)[0]
                bb_ik = mHandleFactory.get_axisBox_size(mProxyHelper.mNode)
    
                _ik_shape = CURVES.create_fromName('cube', size = bb_ik)
                ATTR.set(_ik_shape,'scale', 1.5)
                mIKShape = cgmMeta.validateObjArg(_ik_shape, 'cgmObject',setClass=True)
                #DIST.offsetShape_byVector(_ik_shape,_offset, mIKCrv.p_position,component='cv')
    
                mIKShape.doSnapTo(mProxyHelper)
                pos_ik = POS.get_bb_center(mProxyHelper.mNode)
                #SNAPCALLS.get_special_pos(mEndHandle.p_nameLong,
                #                                   'axisBox','z+',False)                
    
                mIKShape.p_position = pos_ik
                mIKCrv = ml_handleTargets[self.int_handleEndIdx].doCreateAt()
    
                CORERIG.shapeParent_in_place(mIKCrv.mNode, mIKShape.mNode, False)
    
            elif str_ikEnd in ['tipBase','tipEnd','tipMid']:
                log.debug("|{0}| >> tip shape...".format(_str_func))
    
                ml_curves = []
    
                if str_ikEnd == 'tipBase':
                    mIKCrv = ml_handleTargets[self.int_handleEndIdx].doCreateAt()
                elif str_ikEnd == 'tipMid':
                    mIKCrv = ml_handleTargets[self.int_handleEndIdx].doCreateAt()
                    
                    pos = DIST.get_average_position([ml_rigJoints[self.int_segBaseIdx].p_position,
                                                     ml_rigJoints[-1].p_position])
                    
                    mIKCrv.p_position = pos
                    
                else:
                    mIKCrv = ml_handleTargets[-1].doCreateAt()
                    #if self.b_ikNeedEnd:
                        #SNAP.go(mIKCrv.mNode,
                            #ml_prerigHandles[-1].jointHelper,
                            #rotation = False)
                """
                    for mObj in ml_templateHandles[-2:]:
                        mCrv = mObj.loftCurve.doDuplicate(po=False,ic=False)
                        DIST.offsetShape_byVector(mCrv.mNode,_offset, mCrv.p_position,component='cv')
                        mCrv.p_parent=False
                        for mShape in mCrv.getShapes(asMeta=True):
                            mShape.overrideDisplayType = False
                        CORERIG.shapeParent_in_place(mIKCrv.mNode, mCrv.mNode, True)
                        ml_curves.append(mCrv)
    
                    #pprint.pprint(d_endPos)
                    for mCrv in ml_curves:
                        mCrv.delete()                """
                CORERIG.shapeParent_in_place(mIKCrv.mNode, ml_fkShapes[-1].mNode, True)
            else:
                log.debug("|{0}| >> default IK shape...".format(_str_func))
                mIK_templateHandle = ml_templateHandles[ self.int_handleEndIdx ]
                bb_ik = mHandleFactory.get_axisBox_size(mIK_templateHandle.mNode)
                _ik_shape = CURVES.create_fromName('cube', size = bb_ik)
                ATTR.set(_ik_shape,'scale', 1.1)
                
                mIKShape = cgmMeta.validateObjArg(_ik_shape, 'cgmObject',setClass=True)
        
                mIKShape.doSnapTo(mIK_templateHandle)
                #pos_ik = POS.get_bb_center(mProxyHelper.mNode)
                #SNAPCALLS.get_special_pos(mEndHandle.p_nameLong,
                #                                   'axisBox','z+',False)                
        
                #mIKShape.p_position = pos_ik
                mIKCrv = ml_ikJoints[self.int_handleEndIdx].doCreateAt()
        
                CORERIG.shapeParent_in_place(mIKCrv.mNode, mIKShape.mNode, False)                
                
    
            mHandleFactory.color(mIKCrv.mNode, controlType = 'main',transparent=True)
            mIKCrv.doCopyNameTagsFromObject(ml_fkJoints[self.int_handleEndIdx].mNode,
                                            ignore=['cgmType','cgmTypeModifier'])
            mIKCrv.doStore('cgmTypeModifier','ik')
            mIKCrv.doStore('cgmType','handle')
            mIKCrv.doName()
    
    
            mHandleFactory.color(mIKCrv.mNode, controlType = 'main')        
            self.mRigNull.connectChildNode(mIKCrv,'controlIK','rigNull')#Connect
    
        #IK base ---------------------------------------------------------------------------------
        if mBlock.ikBase:
            log.debug("|{0}| >> ikBase Handle...".format(_str_func))
    
            if str_ikBase in ['hips','simple']:
                if str_ikBase ==  'hips':
                    mIKBaseCrv = ml_ikJoints[1].doCreateAt(setClass=True)
                    mIKBaseCrv.doCopyNameTagsFromObject(ml_fkJoints[0].mNode,ignore=['cgmType'])                
                    mIKBaseCrv.doStore('cgmName','hips')
                else:
                    mIKBaseCrv = ml_ikJoints[0].doCreateAt(setClass=True)
                    mIKBaseCrv.doCopyNameTagsFromObject(ml_fkJoints[0].mNode,ignore=['cgmType'])
                    
                CORERIG.shapeParent_in_place(mIKBaseCrv.mNode, ml_fkShapes[0].mNode, True)
                
            else:
                log.debug("|{0}| >> default IK base shape...".format(_str_func))
                mIK_templateHandle = ml_templateHandles[ 0 ]
                bb_ik = mHandleFactory.get_axisBox_size(mIK_templateHandle.mNode)
                _ik_shape = CURVES.create_fromName('cube', size = bb_ik)
                ATTR.set(_ik_shape,'scale', 1.1)
            
                mIKBaseShape = cgmMeta.validateObjArg(_ik_shape, 'cgmObject',setClass=True)
            
                mIKBaseShape.doSnapTo(mIK_templateHandle)
                #pos_ik = POS.get_bb_center(mProxyHelper.mNode)
                #SNAPCALLS.get_special_pos(mEndHandle.p_nameLong,
                #                                   'axisBox','z+',False)                
            
                #mIKBaseShape.p_position = pos_ik
                mIKBaseCrv = ml_ikJoints[0].doCreateAt()
                mIKBaseCrv.doCopyNameTagsFromObject(ml_fkJoints[0].mNode,ignore=['cgmType'])
                CORERIG.shapeParent_in_place(mIKBaseCrv.mNode, mIKBaseShape.mNode, False)                            
    
            mIKBaseCrv.doStore('cgmTypeModifier','ikBase')
            mIKBaseCrv.doName()
    
            """
                for mObj in ml_templateHandles[:2]:
                    mCrv = mObj.loftCurve.doDuplicate(po=False,ic=False)
                    DIST.offsetShape_byVector(mCrv.mNode,_offset, mCrv.p_position,component='cv')
                    mCrv.p_parent=False
                    for mShape in mCrv.getShapes(asMeta=True):
                        mShape.overrideDisplayType = False
    
                    CORERIG.shapeParent_in_place(mIKBaseCrv.mNode, mCrv.mNode, False)
                    #ml_curves.append(mCrv)
    
                    #pprint.pprint(d_endPos)
                    #for mCrv in ml_curves:
                        #try:mc.lockNode(mCrv.mNode,lock=False)
                        #except:pass
                        #mCrv.delete()            """
            mHandleFactory.color(mIKBaseCrv.mNode, controlType = 'main',transparent=True)
    
    
            #CORERIG.match_transform(mIKBaseCrv.mNode,ml_ikJoints[0].mNode)
            mHandleFactory.color(mIKBaseCrv.mNode, controlType = 'main')        
            self.mRigNull.connectChildNode(mIKBaseCrv,'controlIKBase','rigNull')#Connect        
        
        
        #FK=============================================================================================    
        log.debug("|{0}| >> Frame shape cast...".format(_str_func))
        ml_fkShapesSimple = self.atBuilderUtils('shapes_fromCast',
                                          offset = _offset,
                                          mode = 'simpleCast')
                                          #mode = 'frameHandle')
        
        
        log.debug("|{0}| >> FK...".format(_str_func))    
        for i,mCrv in enumerate(ml_fkShapesSimple):
            mJnt = ml_fkJoints[i]
            #CORERIG.match_orientation(mCrv.mNode,mJnt.mNode)
            
            if i == 0 and str_ikBase == 'hips':
                log.debug("|{0}| >> FK hips. no shape on frame...".format(_str_func))
                mCrv.delete()
                continue
            else:
                mHandleFactory.color(mCrv.mNode, controlType = 'main')        
                CORERIG.shapeParent_in_place(mJnt.mNode,mCrv.mNode, False, replaceShapes=True)
                

        for mShape in ml_fkShapes:
            mShape.delete()        
        return
    except Exception,err:cgmGEN.cgmException(Exception,err)
    



@cgmGEN.Timer
def rig_controls(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_controls'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug(self)
    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    ml_controlsAll = []#we'll append to this list and connect them all at the end
    mRootParent = self.mDeformNull
    mSettings = mRigNull.settings
    
    b_cog = False
    if mBlock.getMessage('cogHelper'):
        b_cog = True
    str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')
    
    d_controlSpaces = self.atBuilderUtils('get_controlSpaceSetupDict')
    
    # Drivers ==============================================================================================
    log.debug("|{0}| >> Attr drivers...".format(_str_func))    
    if mBlock.ikSetup:
        log.debug("|{0}| >> Build IK drivers...".format(_str_func))
        mPlug_FKIK = cgmMeta.cgmAttr(mSettings.mNode,'FKIK',attrType='float',minValue=0,maxValue=1,lock=False,keyable=True)
    
    #>> vis Drivers ====================================================================================
    mPlug_visSub = self.atBuilderUtils('build_visSub')
    
    if not b_cog:
        mPlug_visRoot = cgmMeta.cgmAttr(mSettings,'visRoot', value = True,
                                        attrType='bool', defaultValue = False,
                                        keyable = False,hidden = False)
    mPlug_visDirect = cgmMeta.cgmAttr(mSettings,'visDirect', value = True,
                                      attrType='bool', defaultValue = False,
                                      keyable = False,hidden = False)
    
    #if self.mBlock.headAim:        
        #mPlug_aim = cgmMeta.cgmAttr(mSettings.mNode,'blend_aim',attrType='float',minValue=0,maxValue=1,lock=False,keyable=True)
        
    
    #Root ==============================================================================================
    log.debug("|{0}| >> Root...".format(_str_func))
    
    if not mRigNull.getMessage('rigRoot'):
        raise ValueError,"No rigRoot found"
    
    mRoot = mRigNull.rigRoot
    log.debug("|{0}| >> Found rigRoot : {1}".format(_str_func, mRoot))
    
    
    _d = MODULECONTROL.register(mRoot,
                                addDynParentGroup = True,
                                mirrorSide= self.d_module['mirrorDirection'],
                                mirrorAxis="translateX,rotateY,rotateZ",
                                makeAimable = True,
                                **d_controlSpaces)
    
    mRoot = _d['mObj']
    mRoot.masterGroup.parent = mRootParent
    mRootParent = mRoot#Change parent going forward...
    ml_controlsAll.append(mRoot)
    
    if not b_cog:
        for mShape in mRoot.getShapes(asMeta=True):
            ATTR.connect(mPlug_visRoot.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))
            
    #FK controls ==============================================================================================
    log.debug("|{0}| >> FK Controls...".format(_str_func))
    ml_fkJoints = self.mRigNull.msgList_get('fkJoints')
    
    if str_ikBase == 'hips':
        ml_fkJoints = ml_fkJoints[1:]
    
    ml_fkJoints[0].parent = mRoot
    ml_controlsAll.extend(ml_fkJoints)
    
    for i,mObj in enumerate(ml_fkJoints):
        d_buffer = MODULECONTROL.register(mObj,
                                          mirrorSide= self.d_module['mirrorDirection'],
                                          mirrorAxis="translateX,rotateY,rotateZ",
                                          makeAimable = True)

        mObj = d_buffer['mObj']
        ATTR.set_hidden(mObj.mNode,'radius',True)
            
    
    #ControlIK ========================================================================================
    mControlIK = False
    if mRigNull.getMessage('controlIK'):
        ml_blend = mRigNull.msgList_get('blendJoints')
        
        mControlIK = mRigNull.controlIK
        log.debug("|{0}| >> Found controlIK : {1}".format(_str_func, mControlIK))
        
        _d = MODULECONTROL.register(mControlIK,
                                    addDynParentGroup = True, 
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = True,
                                    **d_controlSpaces)
        
        mControlIK = _d['mObj']
        mControlIK.masterGroup.parent = mRootParent
        ml_controlsAll.append(mControlIK)
        
        #Register our snapToTarget -------------------------------------------------------------
        self.atUtils('get_switchTarget', mControlIK,ml_blend[self.int_handleEndIdx])
        """
        mSnapTarget = mControlIK.doCreateAt(setClass=True)
        mSnapTarget.p_parent = ml_blend[self.int_handleEndIdx]
        mControlIK.doStore('switchTarget',mSnapTarget.mNode)
        mSnapTarget.rename("{0}_switchTarget".format(mControlIK.p_nameBase))
        log.debug("|{0}| >> IK handle snap target : {1}".format(_str_func, mSnapTarget))
        mSnapTarget.setAttrFlags()"""
        
    mControlBaseIK = False
    if mRigNull.getMessage('controlIKBase'):
        mControlBaseIK = mRigNull.controlIKBase
        log.debug("|{0}| >> Found controlBaseIK : {1}".format(_str_func, mControlBaseIK))
        
        _d = MODULECONTROL.register(mControlBaseIK,
                                    addDynParentGroup = True, 
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = True,
                                    **d_controlSpaces)
                                    
        
        mControlBaseIK = _d['mObj']
        mControlBaseIK.masterGroup.parent = mRootParent
        ml_controlsAll.append(mControlBaseIK)
        
        #Register our snapToTarget -------------------------------------------------------------
        self.atUtils('get_switchTarget', mControlBaseIK,ml_blend[0])
        """
        mSnapTarget = mControlBaseIK.doCreateAt(setClass=True)
        mControlBaseIK.doStore('switchTarget',mSnapTarget.mNode)
        mSnapTarget.rename("{0}_switchTarget".format(mControlBaseIK.p_nameBase))
        log.debug("|{0}| >> IK Base handle snap target : {1}".format(_str_func, mSnapTarget))
        mSnapTarget.p_parent = ml_blend[0]        
        mSnapTarget.setAttrFlags()"""
        
        
    mControlSegMidIK = False
    #controlSegMidIK =============================================================================
    if mRigNull.getMessage('controlSegMidIK'):
        mControlSegMidIK = mRigNull.controlSegMidIK
        log.debug("|{0}| >> found controlSegMidIK: {1}".format(_str_func,mControlSegMidIK))
        
        _d = MODULECONTROL.register(mControlSegMidIK,
                                    addDynParentGroup = True, 
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = True,
                                    **d_controlSpaces)
        
        
        mControlSegMidIK = _d['mObj']
        mControlSegMidIK.masterGroup.parent = mRootParent
        ml_controlsAll.append(mControlSegMidIK)
    
        #Register our snapToTarget -------------------------------------------------------------
        self.atUtils('get_switchTarget', mControlSegMidIK,ml_blend[ MATH.get_midIndex(len(ml_blend))])        


    if not b_cog:#>> settings ========================================================================================
        log.debug("|{0}| >> Settings : {1}".format(_str_func, mSettings))
        
        MODULECONTROL.register(mSettings,
                               mirrorSide= self.d_module['mirrorDirection'],
                               )
    
        #ml_blendJoints = self.mRigNull.msgList_get('blendJoints')
        #if ml_blendJoints:
        #    mSettings.masterGroup.parent = ml_blendJoints[-1]
        #else:
        #    mSettings.masterGroup.parent = ml_fkJoints[-1]
    
    #>> handleJoints ========================================================================================
    ml_handleJoints = self.mRigNull.msgList_get('handleJoints')
    if ml_handleJoints:
        log.debug("|{0}| >> Found Handle Joints...".format(_str_func))
        
        ml_controlsAll.extend(ml_handleJoints)
        

        for i,mObj in enumerate(ml_handleJoints):
            d_buffer = MODULECONTROL.register(mObj,
                                              mirrorSide= self.d_module['mirrorDirection'],
                                              mirrorAxis="translateX,rotateY,rotateZ",
                                              makeAimable = False)
    
            mObj = d_buffer['mObj']
            ATTR.set_hidden(mObj.mNode,'radius',True)
            
            for mShape in mObj.getShapes(asMeta=True):
                ATTR.connect(mPlug_visSub.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))
        
            
    #>> Direct Controls ==================================================================================
    log.debug("|{0}| >> Direct controls...".format(_str_func))
    
    ml_rigJoints = self.mRigNull.msgList_get('rigJoints')
    ml_controlsAll.extend(ml_rigJoints)
    
    for i,mObj in enumerate(ml_rigJoints):
        d_buffer = MODULECONTROL.register(mObj,
                                          typeModifier='direct',
                                          mirrorSide= self.d_module['mirrorDirection'],
                                          mirrorAxis="translateX,rotateY,rotateZ",
                                          makeAimable = False)

        mObj = d_buffer['mObj']
        ATTR.set_hidden(mObj.mNode,'radius',True)        
        if mObj.hasAttr('cgmIterator'):
            ATTR.set_hidden(mObj.mNode,'cgmIterator',True)        
            
        for mShape in mObj.getShapes(asMeta=True):
            ATTR.connect(mPlug_visDirect.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))
                
    
    self.atBuilderUtils('check_nameMatches', ml_controlsAll)
    
    mHandleFactory = mBlock.asHandleFactory()
    for mCtrl in ml_controlsAll:
        ATTR.set(mCtrl.mNode,'rotateOrder',self.rotateOrder)
        
        if mCtrl.hasAttr('radius'):
            ATTR.set(mCtrl.mNode,'radius',0)        
        
        ml_pivots = mCtrl.msgList_get('spacePivots')
        if ml_pivots:
            log.debug("|{0}| >> Coloring spacePivots for: {1}".format(_str_func,mCtrl))
            for mPivot in ml_pivots:
                mHandleFactory.color(mPivot.mNode, controlType = 'sub')        

    
    #ml_controlsAll = self.atBuilderUtils('register_mirrorIndices', ml_controlsAll)
    mRigNull.msgList_connect('controlsAll',ml_controlsAll)
    mRigNull.moduleSet.extend(ml_controlsAll)
    
    return 


@cgmGEN.Timer
def rig_segments(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_segments'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug(self)    

    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    ml_rigJoints = mRigNull.msgList_get('rigJoints')
    ml_segJoints = mRigNull.msgList_get('segmentJoints')
    mModule = self.mModule
    mRoot = mRigNull.rigRoot
    
    if len(ml_rigJoints)<2:
        log.debug("|{0}| >> Not enough rig joints for setup".format(_str_func))                      
        return True
    
    
    mRootParent = self.mDeformNull
    if not ml_segJoints:
        log.debug("|{0}| >> No segment joints. No segment setup necessary.".format(_str_func))
        return True
    
    ml_handleJoints = mRigNull.msgList_get('handleJoints')
    
    for mJnt in ml_segJoints:
        mJnt.drawStyle = 2
        ATTR.set(mJnt.mNode,'radius',0)
    
    #>> Ribbon setup ========================================================================================
    log.debug("|{0}| >> Ribbon setup...".format(_str_func))
    
    _settingsControl = None
    if mBlock.squashExtraControl:
        _settingsControl = mRigNull.settings.mNode
    
    _extraSquashControl = mBlock.squashExtraControl
           
    res_segScale = self.UTILS.get_blockScale(self,'segMeasure')
    mPlug_masterScale = res_segScale[0]
    mMasterCurve = res_segScale[1]
    
    
    _d = {'jointList':[mObj.mNode for mObj in ml_segJoints],
          'baseName':'{0}_rigRibbon'.format(self.d_module['partName']),
          'connectBy':'constraint',
          'extendEnds':True,
          'additiveScaleEnds':True,
          'masterScalePlug':mPlug_masterScale,
          'influences':ml_handleJoints,
          'settingsControl':_settingsControl,
          'attachEndsToInfluences':True,
          'moduleInstance':mModule}
    reload(IK)
    _d.update(self.d_squashStretch)
    res_ribbon = IK.ribbon(**_d)
    
    ml_surfaces = res_ribbon['mlSurfaces']
    
    mMasterCurve.p_parent = mRoot
    
    """
    #Setup the aim along the chain -----------------------------------------------------------------------------
    for i,mJnt in enumerate(ml_rigJoints):
        mAimGroup = mJnt.doGroup(True,asMeta=True,typeModifier = 'aim')
        v_aim = [0,0,1]
        if mJnt == ml_rigJoints[-1]:
            s_aim = ml_rigJoints[-2].masterGroup.mNode
            v_aim = [0,0,-1]
        else:
            s_aim = ml_rigJoints[i+1].masterGroup.mNode
    
        mc.aimConstraint(s_aim, mAimGroup.mNode, maintainOffset = True, #skip = 'z',
                         aimVector = v_aim, upVector = [1,0,0], worldUpObject = mJnt.masterGroup.mNode,
                         worldUpType = 'objectrotation', worldUpVector = [1,0,0])    
    """
    """
    for mSurf in ml_surfaces:
        mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_handleJoints],
                                                              mSurf.mNode,
                                                              tsb=True,
                                                              maximumInfluences = 3,
                                                              normalizeWeights = 1,dropoffRate=2.5),
                                              'cgmNode',
                                              setClass=True)
    
        mSkinCluster.doStore('cgmName', mSurf.mNode)
        mSkinCluster.doName()    
        
        reload(CORESKIN)
        CORESKIN.surface_tightenEnds(mSurf.mNode,
                                     ml_handleJoints[0].mNode,
                                     ml_handleJoints[-1].mNode,
                                     blendLength=4, hardLength=2,
                                     mode = None)    """
    
    cgmGEN.func_snapShot(vars())
    ml_segJoints[0].parent = mRoot
    
    if self.b_squashSetup:
        for mJnt in ml_segJoints:
            mJnt.segmentScaleCompensate = False
            if mJnt == ml_segJoints[0]:
                continue
            mJnt.p_parent = ml_segJoints[0].p_parent        

    
@cgmGEN.Timer
def rig_frame(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_rigFrame'.format(_short)
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug(self)        
        mBlock = self.mBlock
        mRigNull = self.mRigNull
        mRootParent = self.mDeformNull
        mModule = self.mModule
        
        ml_rigJoints = mRigNull.msgList_get('rigJoints')
        ml_fkJoints = mRigNull.msgList_get('fkJoints')
        ml_handleJoints = mRigNull.msgList_get('handleJoints')
        ml_baseIKDrivers = mRigNull.msgList_get('baseIKDrivers')
        ml_blendJoints = mRigNull.msgList_get('blendJoints')
        mPlug_globalScale = self.d_module['mPlug_globalScale']
        mRoot = mRigNull.rigRoot
        
        b_cog = False
        if mBlock.getMessage('cogHelper'):
            b_cog = True
        str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')        
        
        mIKBaseControl = False
        if mRigNull.getMessage('controlIKBase'):
            mIKBaseControl = mRigNull.controlIKBase
        
        #>> handleJoints =====================================================================================
        if ml_handleJoints:
            log.debug("|{0}| >> Handles setup...".format(_str_func))
            
            ml_handleParents = ml_fkJoints
            if ml_blendJoints:
                log.debug("|{0}| >> Handles parent: blend".format(_str_func))
                ml_handleParents = ml_blendJoints            
            
            if str_ikBase == 'hips':
                log.debug("|{0}| >> hips setup...".format(_str_func))
                
                ml_ribbonIkHandles = mRigNull.msgList_get('ribbonIKDrivers')
                if not ml_ribbonIkHandles:
                    raise ValueError,"No ribbon IKDriversFound"
                

            if len(ml_handleJoints) == 1:
                mHipHandle = ml_handleJoints[0]
                
                reload(RIGCONSTRAINT)
                RIGCONSTRAINT.build_aimSequence(ml_handleJoints,
                                                ml_ribbonIkHandles,
                                                [mRigNull.controlIKBase.mNode],#ml_handleParents,
                                                mode = 'singleBlend',
                                                upMode = 'objectRotation')
            else:
                if str_ikBase == 'hips':
                    log.debug("|{0}| >> hips handles...".format(_str_func))                    
                    ml_handleJoints[0].masterGroup.p_parent = mIKBaseControl
                    mHipHandle = ml_handleJoints[1]
                    mHipHandle.masterGroup.p_parent = mRoot
                    mc.pointConstraint(mIKBaseControl.mNode,
                                       mHipHandle.masterGroup.mNode,
                                       maintainOffset = True)
                    
                    RIGCONSTRAINT.build_aimSequence(ml_handleJoints[1],
                                                    ml_ribbonIkHandles,
                                                    [mRigNull.controlIKBase.mNode],#ml_handleParents,
                                                    mode = 'singleBlend',
                                                    upMode = 'objectRotation')
                    """
                    RIGCONSTRAINT.build_aimSequence(ml_handleJoints[-1],
                                                    ml_ribbonIkHandles,
                                                     #[mRigNull.controlIK.mNode],#ml_handleParents,
                                                    mode = 'singleBlend',
                                                    upMode = 'objectRotation')"""
                    
                    for i,mHandle in enumerate(ml_handleJoints):
                        if mHandle in ml_handleJoints[:2]:# + [ml_handleJoints[-1]]:
                            continue
                        
                        mHandle.masterGroup.parent = ml_handleParents[i]
                        s_rootTarget = False
                        s_targetForward = False
                        s_targetBack = False
                        mMasterGroup = mHandle.masterGroup
                        b_first = False
                        if mHandle == ml_handleJoints[0]:
                            log.debug("|{0}| >> First handle: {1}".format(_str_func,mHandle))
                            if len(ml_handleJoints) <=2:
                                s_targetForward = ml_handleParents[-1].mNode
                            else:
                                s_targetForward = ml_handleJoints[i+1].getMessage('masterGroup')[0]
                            s_rootTarget = mRoot.mNode
                            b_first = True
                    
                        elif mHandle == ml_handleJoints[-1]:
                            log.debug("|{0}| >> Last handle: {1}".format(_str_func,mHandle))
                            s_rootTarget = ml_handleParents[i].mNode                
                            s_targetBack = ml_handleJoints[i-1].getMessage('masterGroup')[0]
                        else:
                            log.debug("|{0}| >> Reg handle: {1}".format(_str_func,mHandle))            
                            s_targetForward = ml_handleJoints[i+1].getMessage('masterGroup')[0]
                            s_targetBack = ml_handleJoints[i-1].getMessage('masterGroup')[0]
                    
                        #Decompose matrix for parent...
                        mUpDecomp = cgmMeta.cgmNode(nodeType = 'decomposeMatrix')
                        mUpDecomp.doStore('cgmName',ml_handleParents[i].mNode)                
                        mUpDecomp.addAttr('cgmType','aimMatrix',attrType='string',lock=True)
                        mUpDecomp.doName()
                    
                        ATTR.connect("%s.worldMatrix"%(ml_handleParents[i].mNode),"%s.%s"%(mUpDecomp.mNode,'inputMatrix'))
                    
                        if s_targetForward:
                            mAimForward = mHandle.doCreateAt()
                            mAimForward.parent = mMasterGroup            
                            mAimForward.doStore('cgmTypeModifier','forward')
                            mAimForward.doStore('cgmType','aimer')
                            mAimForward.doName()
                    
                            _const=mc.aimConstraint(s_targetForward, mAimForward.mNode, maintainOffset = True, #skip = 'z',
                                                    aimVector = [0,0,1], upVector = [1,0,0], worldUpObject = ml_handleParents[i].mNode,
                                                    worldUpType = 'vector', worldUpVector = [0,0,0])            
                            s_targetForward = mAimForward.mNode
                            ATTR.connect("%s.%s"%(mUpDecomp.mNode,"outputRotate"),"%s.%s"%(_const[0],"upVector"))                 
                    
                        else:
                            s_targetForward = ml_handleParents[i].mNode
                    
                        if s_targetBack:
                            mAimBack = mHandle.doCreateAt()
                            mAimBack.parent = mMasterGroup                        
                            mAimBack.doStore('cgmTypeModifier','back')
                            mAimBack.doStore('cgmType','aimer')
                            mAimBack.doName()
                    
                            _const = mc.aimConstraint(s_targetBack, mAimBack.mNode, maintainOffset = True, #skip = 'z',
                                                      aimVector = [0,0,-1], upVector = [1,0,0], worldUpObject = ml_handleParents[i].mNode,
                                                      worldUpType = 'vector', worldUpVector = [0,0,0])  
                            s_targetBack = mAimBack.mNode
                            ATTR.connect("%s.%s"%(mUpDecomp.mNode,"outputRotate"),"%s.%s"%(_const[0],"upVector"))                                     
                        else:
                            s_targetBack = s_rootTarget
                            #ml_handleParents[i].mNode
                    
                        pprint.pprint([s_targetForward,s_targetBack])
                        mAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')
                    
                        mHandle.parent = False
                    
                        if b_first:
                            const = mc.orientConstraint([s_targetBack, s_targetForward], mAimGroup.mNode, maintainOffset = True)[0]
                        else:
                            const = mc.orientConstraint([s_targetForward, s_targetBack], mAimGroup.mNode, maintainOffset = True)[0]
                    
                    
                        d_blendReturn = NODEFACTORY.createSingleBlendNetwork([mHandle.mNode,'followRoot'],
                                                                             [mHandle.mNode,'resultRootFollow'],
                                                                             [mHandle.mNode,'resultAimFollow'],
                                                                             keyable=True)
                        targetWeights = mc.orientConstraint(const,q=True, weightAliasList=True,maintainOffset=True)
                    
                        #Connect                                  
                        d_blendReturn['d_result1']['mi_plug'].doConnectOut('%s.%s' % (const,targetWeights[0]))
                        d_blendReturn['d_result2']['mi_plug'].doConnectOut('%s.%s' % (const,targetWeights[1]))
                        d_blendReturn['d_result1']['mi_plug'].p_hidden = True
                        d_blendReturn['d_result2']['mi_plug'].p_hidden = True
                    
                        mHandle.parent = mAimGroup#...parent back
                    
                        if mHandle in [ml_handleJoints[0],ml_handleJoints[-1]]:
                            mHandle.followRoot = 1
                        else:
                            mHandle.followRoot = .5
                        

                else:
                    log.debug("|{0}| >> reg handles...".format(_str_func))
                    for i,mHandle in enumerate(ml_handleJoints):
                        mHandle.masterGroup.parent = ml_handleParents[i]
                        s_rootTarget = False
                        s_targetForward = False
                        s_targetBack = False
                        mMasterGroup = mHandle.masterGroup
                        b_first = False
                        if mHandle == ml_handleJoints[0]:
                            log.debug("|{0}| >> First handle: {1}".format(_str_func,mHandle))
                            if len(ml_handleJoints) <=2:
                                s_targetForward = ml_handleParents[-1].mNode
                            else:
                                s_targetForward = ml_handleJoints[i+1].getMessage('masterGroup')[0]
                            s_rootTarget = mRoot.mNode
                            b_first = True
                            
                        elif mHandle == ml_handleJoints[-1]:
                            log.debug("|{0}| >> Last handle: {1}".format(_str_func,mHandle))
                            s_rootTarget = ml_handleParents[i].mNode                
                            s_targetBack = ml_handleJoints[i-1].getMessage('masterGroup')[0]
                        else:
                            log.debug("|{0}| >> Reg handle: {1}".format(_str_func,mHandle))            
                            s_targetForward = ml_handleJoints[i+1].getMessage('masterGroup')[0]
                            s_targetBack = ml_handleJoints[i-1].getMessage('masterGroup')[0]
                            
                        #Decompose matrix for parent...
                        mUpDecomp = cgmMeta.cgmNode(nodeType = 'decomposeMatrix')
                        mUpDecomp.doStore('cgmName',ml_handleParents[i].mNode)                
                        mUpDecomp.addAttr('cgmType','aimMatrix',attrType='string',lock=True)
                        mUpDecomp.doName()
                        
                        ATTR.connect("%s.worldMatrix"%(ml_handleParents[i].mNode),"%s.%s"%(mUpDecomp.mNode,'inputMatrix'))
                        
                        if s_targetForward:
                            mAimForward = mHandle.doCreateAt()
                            mAimForward.parent = mMasterGroup            
                            mAimForward.doStore('cgmTypeModifier','forward')
                            mAimForward.doStore('cgmType','aimer')
                            mAimForward.doName()
                            
                            _const=mc.aimConstraint(s_targetForward, mAimForward.mNode, maintainOffset = True, #skip = 'z',
                                                    aimVector = [0,0,1], upVector = [1,0,0], worldUpObject = ml_handleParents[i].mNode,
                                                    worldUpType = 'vector', worldUpVector = [0,0,0])            
                            s_targetForward = mAimForward.mNode
                            ATTR.connect("%s.%s"%(mUpDecomp.mNode,"outputRotate"),"%s.%s"%(_const[0],"upVector"))                 
                            
                        else:
                            s_targetForward = ml_handleParents[i].mNode
                            
                        if s_targetBack:
                            mAimBack = mHandle.doCreateAt()
                            mAimBack.parent = mMasterGroup                        
                            mAimBack.doStore('cgmTypeModifier','back')
                            mAimBack.doStore('cgmType','aimer')
                            mAimBack.doName()
                            
                            _const = mc.aimConstraint(s_targetBack, mAimBack.mNode, maintainOffset = True, #skip = 'z',
                                                      aimVector = [0,0,-1], upVector = [1,0,0], worldUpObject = ml_handleParents[i].mNode,
                                                      worldUpType = 'vector', worldUpVector = [0,0,0])  
                            s_targetBack = mAimBack.mNode
                            ATTR.connect("%s.%s"%(mUpDecomp.mNode,"outputRotate"),"%s.%s"%(_const[0],"upVector"))                                     
                        else:
                            s_targetBack = s_rootTarget
                            #ml_handleParents[i].mNode
                        
                        #pprint.pprint([s_targetForward,s_targetBack])
                        mAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')
                        
                        mHandle.parent = False
                        
                        if b_first:
                            const = mc.orientConstraint([s_targetBack, s_targetForward], mAimGroup.mNode, maintainOffset = True)[0]
                        else:
                            const = mc.orientConstraint([s_targetForward, s_targetBack], mAimGroup.mNode, maintainOffset = True)[0]
                            
            
                        d_blendReturn = NODEFACTORY.createSingleBlendNetwork([mHandle.mNode,'followRoot'],
                                                                             [mHandle.mNode,'resultRootFollow'],
                                                                             [mHandle.mNode,'resultAimFollow'],
                                                                             keyable=True)
                        targetWeights = mc.orientConstraint(const,q=True, weightAliasList=True,maintainOffset=True)
                        
                        #Connect                                  
                        d_blendReturn['d_result1']['mi_plug'].doConnectOut('%s.%s' % (const,targetWeights[0]))
                        d_blendReturn['d_result2']['mi_plug'].doConnectOut('%s.%s' % (const,targetWeights[1]))
                        d_blendReturn['d_result1']['mi_plug'].p_hidden = True
                        d_blendReturn['d_result2']['mi_plug'].p_hidden = True
                        
                        mHandle.parent = mAimGroup#...parent back
                        
                        if mHandle in [ml_handleJoints[0],ml_handleJoints[-1]]:
                            mHandle.followRoot = 1
                        else:
                            mHandle.followRoot = .5
                        

    

            
            """
            ml_handleJoints[-1].masterGroup.parent = mHeadFK
            ml_handleJoints[0].masterGroup.parent = mRoot
            
            #Aim top to bottom ----------------------------
            mc.aimConstraint(ml_handleJoints[0].mNode,
                             ml_handleJoints[-1].masterGroup.mNode,
                             maintainOffset = True, weight = 1,
                             aimVector = self.d_orientation['vectorAimNeg'],
                             upVector = self.d_orientation['vectorUp'],
                             worldUpVector = self.d_orientation['vectorOut'],
                             worldUpObject = mTopHandleDriver.mNode,
                             worldUpType = 'objectRotation' )
            
            #Aim bottom to top ----------------------------
            mc.aimConstraint(ml_handleJoints[-1].mNode,
                             ml_handleJoints[0].masterGroup.mNode,
                             maintainOffset = True, weight = 1,
                             aimVector = self.d_orientation['vectorAim'],
                             upVector = self.d_orientation['vectorUp'],
                             worldUpVector = self.d_orientation['vectorOut'],
                             worldUpObject = ml_blendJoints[0].mNode,
                             worldUpType = 'objectRotation' )    
                             """
        
        #>> Build IK ======================================================================================
        if mBlock.ikSetup:
            _ikSetup = mBlock.getEnumValueString('ikSetup')
            log.debug("|{0}| >> IK Type: {1}".format(_str_func,_ikSetup))    
        
            if not mRigNull.getMessage('rigRoot'):
                raise ValueError,"No rigRoot found"
            if not mRigNull.getMessage('controlIK'):
                raise ValueError,"No controlIK found"            
            
            mIKControl = mRigNull.controlIK
            mSettings = mRigNull.settings
            ml_ikJoints = mRigNull.msgList_get('ikJoints')
            mPlug_FKIK = cgmMeta.cgmAttr(mSettings.mNode,'FKIK',attrType='float',lock=False,keyable=True)
            _jointOrientation = self.d_orientation['str']
            
            mStart = ml_ikJoints[0]
            mEnd = ml_ikJoints[-1]
            _start = ml_ikJoints[0].mNode
            _end = ml_ikJoints[-1].mNode            
            
            #>>> Setup a vis blend result
            mPlug_FKon = cgmMeta.cgmAttr(mSettings,'result_FKon',attrType='float',defaultValue = 0,keyable = False,lock=True,hidden=True)	
            mPlug_IKon = cgmMeta.cgmAttr(mSettings,'result_IKon',attrType='float',defaultValue = 0,keyable = False,lock=True,hidden=True)	
        
            NODEFACTORY.createSingleBlendNetwork(mPlug_FKIK.p_combinedName,
                                                 mPlug_IKon.p_combinedName,
                                                 mPlug_FKon.p_combinedName)
            
            #IK =====================================================================
            mIKGroup = mRoot.doCreateAt()
            mIKGroup.doStore('cgmTypeModifier','ik')
            mIKGroup.doName()
            
            mPlug_IKon.doConnectOut("{0}.visibility".format(mIKGroup.mNode))
            
            mIKGroup.parent = mRoot
            mIKControl.masterGroup.parent = mIKGroup
            
            mIKBaseControl = False
            if mRigNull.getMessage('controlIKBase'):
                mIKBaseControl = mRigNull.controlIKBase
                
                if str_ikBase == 'hips':
                    mIKBaseControl.masterGroup.parent = mRoot
                else:
                    mIKBaseControl.masterGroup.parent = mIKGroup
                    
            else:#Spin Group
                #=========================================================================================
                log.debug("|{0}| >> spin setup...".format(_str_func))
            
                #Make a spin group
                mSpinGroup = mStart.doGroup(False,False,asMeta=True)
                mSpinGroup.doCopyNameTagsFromObject(self.mModule.mNode, ignore = ['cgmName','cgmType'])	
                mSpinGroup.addAttr('cgmName','{0}NoFlipSpin'.format(self.d_module['partName']))
                mSpinGroup.doName()
            
                mSpinGroup.parent = mRoot
            
                mSpinGroup.doGroup(True,True,typeModifier='zero')
            
                #Setup arg
                mPlug_spin = cgmMeta.cgmAttr(mIKControl,'spin',attrType='float',keyable=True, defaultValue = 0, hidden = False)
                mPlug_spin.doConnectOut("%s.r%s"%(mSpinGroup.mNode,_jointOrientation[0]))                

            if _ikSetup == 'rp':
                log.debug("|{0}| >> rp setup...".format(_str_func,_ikSetup))
                
                #Build the IK ---------------------------------------------------------------------
                _d_ik= {'globalScaleAttr':mPlug_globalScale.p_combinedName,
                        'stretch':'translate',
                        'lockMid':False,
                        'rpHandle':True,
                        'nameSuffix':'noFlip',
                        'controlObject':mIKControl.mNode,
                        'moduleInstance':self.mModule.mNode}
                
                d_ikReturn = IK.handle(_start,_end,**_d_ik)
                
                #Get our no flip position-------------------------------------------------------------------------
                log.debug("|{0}| >> no flip dat...".format(_str_func))
                
                _side = mBlock.atUtils('get_side')
                _dist_ik_noFlip = DIST.get_distance_between_points(mStart.p_position,
                                                                   mEnd.p_position)
                if _side == 'left':#if right, rotate the pivots
                    pos_noFlipOffset = mStart.getPositionByAxisDistance(_jointOrientation[2]+'-',_dist_ik_noFlip)
                else:
                    pos_noFlipOffset = mStart.getPositionByAxisDistance(_jointOrientation[2]+'+',_dist_ik_noFlip)
                
                #No flip -------------------------------------------------------------------------
                log.debug("|{0}| >> no flip setup...".format(_str_func))
                
                mIKHandle = d_ikReturn['mHandle']
                ml_distHandlesNF = d_ikReturn['ml_distHandles']
                mRPHandleNF = d_ikReturn['mRPHandle']
            
                #No Flip RP handle -------------------------------------------------------------------
                mRPHandleNF.p_position = pos_noFlipOffset
            
                mRPHandleNF.doCopyNameTagsFromObject(self.mModule.mNode, ignore = ['cgmName','cgmType'])
                mRPHandleNF.addAttr('cgmName','{0}PoleVector'.format(self.d_module['partName']), attrType = 'string')
                mRPHandleNF.addAttr('cgmTypeModifier','noFlip')
                mRPHandleNF.doName()
            
                if mIKBaseControl:
                    mRPHandleNF.parent = mIKBaseControl.mNode
                else:
                    mRPHandleNF.parent = mSpinGroup.mNode

                #>>>Parent IK handles -----------------------------------------------------------------
                log.debug("|{0}| >> parent ik dat...".format(_str_func,_ikSetup))
                
                mIKHandle.parent = mIKControl.mNode#handle to control	
                for mObj in ml_distHandlesNF[:-1]:
                    mObj.parent = mRoot
                ml_distHandlesNF[-1].parent = mIKControl.mNode#handle to control
            
                #>>> Fix our ik_handle twist at the end of all of the parenting
                IK.handle_fixTwist(mIKHandle,_jointOrientation[0])#Fix the twist
                
                mc.parentConstraint([mIKControl.mNode], ml_ikJoints[-1].mNode, maintainOffset = True)
                
                if mIKBaseControl:
                    ml_ikJoints[0].parent = mRigNull.controlIKBase
                
                if mIKBaseControl:
                    mc.pointConstraint(mIKBaseControl.mNode, ml_ikJoints[0].mNode,maintainOffset=True)
                    
            elif _ikSetup == 'spline':# ==============================================================================
                log.debug("|{0}| >> spline setup...".format(_str_func))
                ml_ribbonIkHandles = mRigNull.msgList_get('ribbonIKDrivers')
                if not ml_ribbonIkHandles:
                    raise ValueError,"No ribbon IKDriversFound"
            
                log.debug("|{0}| >> ribbon ik handles...".format(_str_func))
                
                if mIKBaseControl:
                    ml_ribbonIkHandles[0].parent = mIKBaseControl
                else:
                    ml_ribbonIkHandles[0].parent = mSpinGroup
                    
                ml_ribbonIkHandles[-1].parent = mIKControl
            
                mc.aimConstraint(mIKControl.mNode,
                                 ml_ribbonIkHandles[0].mNode,
                                 maintainOffset = True, weight = 1,
                                 aimVector = self.d_orientation['vectorAim'],
                                 upVector = self.d_orientation['vectorUp'],
                                 worldUpVector = self.d_orientation['vectorOut'],
                                 worldUpObject = mSpinGroup.mNode,
                                 worldUpType = 'objectRotation' )
            
                
                res_spline = IK.spline([mObj.mNode for mObj in ml_ikJoints],
                                       orientation = _jointOrientation,
                                       moduleInstance = self.mModule)
                mSplineCurve = res_spline['mSplineCurve']
                log.debug("|{0}| >> spline curve...".format(_str_func))
                

                #...ribbon skinCluster ---------------------------------------------------------------------
                log.debug("|{0}| >> ribbon skinCluster...".format(_str_func))                
                mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_ribbonIkHandles],
                                                                      mSplineCurve.mNode,
                                                                      tsb=True,
                                                                      maximumInfluences = 2,
                                                                      normalizeWeights = 1,dropoffRate=2.5),
                                                      'cgmNode',
                                                      setClass=True)
            
                mSkinCluster.doStore('cgmName', mSplineCurve.mNode)
                mSkinCluster.doName()    
                cgmGEN.func_snapShot(vars())
                
                
            elif _ikSetup == 'ribbon':#===============================================================================
                log.debug("|{0}| >> ribbon setup...".format(_str_func))
                ml_ribbonIkHandles = mRigNull.msgList_get('ribbonIKDrivers')
                if not ml_ribbonIkHandles:
                    raise ValueError,"No ribbon IKDriversFound"
                
                
                #log.debug("|{0}| >> segmentScale measure...".format(_str_func))
                #res_segScale = self.UTILS.get_blockScale(self,'segMeasure')
                #mPlug_masterScale = res_segScale[0]
                #mMasterCurve = res_segScale[1]                
                
                mSegMidIK = False
                if mRigNull.getMessage('controlSegMidIK'):
                    log.debug("|{0}| >> seg mid IK control found...".format(_str_func))
                    
                    mSegMidIK = mRigNull.controlSegMidIK
                    mSegMidIK.masterGroup.parent = mIKGroup
                        
                    ml_midTrackJoints = copy.copy(ml_ribbonIkHandles)
                    ml_midTrackJoints.insert(1,mSegMidIK)
                    
                    d_mid = {'jointList':[mJnt.mNode for mJnt in ml_midTrackJoints],
                             'baseName' :self.d_module['partName'] + '_midRibbon',
                             'driverSetup':'stableBlend',
                             'squashStretch':None,
                             'msgDriver':'masterGroup',
                             'specialMode':'noStartEnd',
                             'connectBy':'constraint',
                             'influences':ml_ribbonIkHandles,
                             'moduleInstance' : mModule}
                    
                    l_midSurfReturn = IK.ribbon(**d_mid)
                    
                    
                    """
                    mMidSurface = l_midSurfReturn['mlSurfaces'][0]
                    #Skin it...
                    mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_ribbonIkHandles],
                                                                          mMidSurface.mNode,
                                                                          tsb=True,
                                                                          maximumInfluences = 2,
                                                                          normalizeWeights = 1,
                                                                          dropoffRate=1),
                                                          'cgmNode',
                                                          setClass=True)
                  
                    mSkinCluster.doStore('cgmName', mMidSurface.mNode)
                    mSkinCluster.doName()
                    
                    #Tighten the weights...
                    CORESKIN.surface_tightenEnds(mMidSurface.mNode, hardLength=2, mode='twoBlend')
                    
                    """
                    """
                    
                    _jointOrientation = self.d_orientation['str']
                    _offset = self.v_offset                    
                    
                    mSegMidIK = mRigNull.controlSegMidIK
                    mSegMidIK.masterGroup.parent = mIKGroup
                    
                    ml_midTrackJoints = copy.copy(ml_ribbonIkHandles)
                    ml_midTrackJoints.insert(1,mSegMidIK)
                    l_surfaceReturn = IK.ribbon_createSurface([mJnt.mNode for mJnt in ml_midTrackJoints],
                                                           'x')
                    mMidSurface = cgmMeta.asMeta(l_surfaceReturn[0])
                    mMidSurface.doStore('cgmName', 'midIKTrack')
                    mMidSurface.doName()
                    
                    reload(RIGCONSTRAINT)
                    l_attach = RIGCONSTRAINT.attach_toShape(mSegMidIK.masterGroup.mNode,mMidSurface.mNode,'conParent')
                    
                    mFollicle = cgmMeta.asMeta(l_attach[0])
                    
                    mDriver = mSegMidIK.doCreateAt(setClass=True)
                    mDriver.rename("{0}_aimDriver".format(mFollicle.p_nameBase))
                    mDriver.parent = mFollicle
                    mUpGroup = mDriver.doGroup(True,asMeta=True,typeModifier = 'up')                    
                    
                    mUpDriver = mSegMidIK.doCreateAt(setClass=True)
                    mDriver.rename("{0}_upTarget".format(mFollicle.p_nameBase))                    
                    pos = DIST.get_pos_by_axis_dist(mSegMidIK.mNode, _jointOrientation[1]+'+', _offset )
                    mUpDriver.p_position = pos
                    mUpDriver.p_parent = mUpGroup
                    
                    mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_ribbonIkHandles],
                                                                          mMidSurface.mNode,
                                                                          tsb=True,
                                                                          maximumInfluences = 2,
                                                                          normalizeWeights = 1,
                                                                          dropoffRate=1),
                                                          'cgmNode',
                                                          setClass=True)
                    
                    mSkinCluster.doStore('cgmName', mMidSurface.mNode)
                    mSkinCluster.doName()                        
                    """
                
                log.debug("|{0}| >> ribbon ik handles...".format(_str_func))
                
                if mIKBaseControl:
                    ml_ribbonIkHandles[0].parent = mIKBaseControl
                else:
                    ml_ribbonIkHandles[0].parent = mSpinGroup
                    mc.aimConstraint(mIKControl.mNode,
                                     ml_ribbonIkHandles[0].mNode,
                                     maintainOffset = True, weight = 1,
                                     aimVector = self.d_orientation['vectorAim'],
                                     upVector = self.d_orientation['vectorUp'],
                                     worldUpVector = self.d_orientation['vectorOut'],
                                     worldUpObject = mSpinGroup.mNode,
                                     worldUpType = 'objectRotation' )                    
                
                ml_ribbonIkHandles[-1].parent = mIKControl
                
                reload(IK)
                
                ml_skinDrivers = copy.copy(ml_ribbonIkHandles)
                max_influences = 2
                #if str_ikBase == 'hips':
                    #ml_skinDrivers.append(mHipHandle)
                    #max_influences+=1
                    
                if mSegMidIK:
                    ml_skinDrivers.append(mSegMidIK)
                    max_influences+=1
                
                """
                if not mRigNull.msgList_get('segmentJoints'):
                    log.debug("|{0}| >> No segment joints setup...".format(_str_func)+cgmGEN._str_hardBreak)
                    
                    _driverSetup = None
                    if mBlock.ribbonAim:
                        _driverSetup =  mBlock.getEnumValueString('ribbonAim')
                    
                    _squashStretch = None
                    if mBlock.squash:
                        _squashStretch =  mBlock.getEnumValueString('squash')
                        
                    _settingsControl = None
                    if mBlock.squashExtraControl:
                        _settingsControl = mRigNull.settings.mNode
                    
                    _extraSquashControl = mBlock.squashExtraControl
                           
                    res_segScale = self.UTILS.get_blockScale(self,'segMeasure')
                    mPlug_masterScale = res_segScale[0]
                    mMasterCurve = res_segScale[1]
                    
                    d_ik = {'jointList':[mObj.mNode for mObj in ml_ikJoints],
                          'baseName':'{0}_ikRibbon'.format(self.d_module['partName']),
                          'connectBy':'constraint',
                          'extraSquashControl':_extraSquashControl,
                          'masterScalePlug':mPlug_masterScale,
                          'influences':ml_skinDrivers,
                          'settingsControl':mSettings.mNode,
                          'moduleInstance':self.mModule}
                    d_ik.update(self.d_squashStretch)"""
                
                if mRigNull.msgList_get('segmentJoints'):
                    log.debug("|{0}| >> Segment joints setup...".format(_str_func)+cgmGEN._str_hardBreak)                    
                    d_ik = {'jointList':[mObj.mNode for mObj in ml_ikJoints],
                            'baseName' : self.d_module['partName'] + '_ikRibbon',
                            'driverSetup':'stableBlend',
                            'squashStretch':None,
                            'connectBy':'constraint',
                            'squashStretchMain':'arcLength',
                            #masterScalePlug:mPlug_masterScale,
                            'settingsControl': mSettings.mNode,
                            'extraSquashControl':True,
                            'influences':ml_skinDrivers,
                            'moduleInstance' : self.mModule}
                    
                    d_ik.update(self.d_squashStretchIK)
                    res_ribbon = IK.ribbon(**d_ik)
                    
                const = ml_ikJoints[-1].getConstraintsTo(asMeta=True)
                for mConst in const:
                    mConst.delete()
                mc.parentConstraint([mIKControl.mNode], ml_ikJoints[-1].mNode, maintainOffset = True)
                
                """
                #...ribbon skinCluster ---------------------------------------------------------------------
                log.debug("|{0}| >> ribbon skinCluster...".format(_str_func))

                
                
                mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_skinDrivers],
                                                                      mSurf.mNode,
                                                                      tsb=True,
                                                                      maximumInfluences = max_influences,
                                                                      normalizeWeights = 1,dropoffRate=10),
                                                      'cgmNode',
                                                      setClass=True)
            
                mSkinCluster.doStore('cgmName', mSurf.mNode)
                mSkinCluster.doName()    
                
                #Tighten the weights...
                reload(CORESKIN)
                CORESKIN.surface_tightenEnds(mSurf.mNode, ml_ribbonIkHandles[0].mNode,
                                             ml_ribbonIkHandles[-1].mNode, blendLength=5)"""
                
            else:
                raise ValueError,"Not implemented {0} ik setup".format(_ikSetup)
            
            
            #Parent --------------------------------------------------
            #Fk...
            if str_ikBase == 'hips':
                mPlug_FKon.doConnectOut("{0}.visibility".format(ml_fkJoints[1].masterGroup.mNode))
                ml_fkJoints[0].p_parent = mIKBaseControl
            else:
                mPlug_FKon.doConnectOut("{0}.visibility".format(ml_fkJoints[0].masterGroup.mNode))            
            
            
            ml_blendJoints[0].parent = mRoot
            ml_ikJoints[0].parent = mIKGroup
            

            #Setup blend ----------------------------------------------------------------------------------
            if self.b_scaleSetup:
                log.debug("|{0}| >> scale blend chain setup...".format(_str_func))                
                RIGCONSTRAINT.blendChainsBy(ml_fkJoints,ml_ikJoints,ml_blendJoints,
                                            driver = mPlug_FKIK.p_combinedName,
                                            l_constraints=['point','orient','scale'])
                
                
                #Scale setup for ik joints                
                ml_ikScaleTargets = [mIKControl]

                if mIKBaseControl:
                    mc.scaleConstraint(mIKBaseControl.mNode, ml_ikJoints[0].mNode,maintainOffset=True)
                    ml_ikScaleTargets.append(mIKBaseControl)
                else:
                    mc.scaleConstraint(mRoot.mNode, ml_ikJoints[0].mNode,maintainOffset=True)
                    ml_ikScaleTargets.append(mRoot)
                    
                mc.scaleConstraint(mIKControl.mNode, ml_ikJoints[-1].mNode,maintainOffset=True)
                
                _targets = [mHandle.mNode for mHandle in ml_ikScaleTargets]
                
                #Scale setup for mid set IK
                if mSegMidIK:
                    mMasterGroup = mSegMidIK.masterGroup
                    _vList = DIST.get_normalizedWeightsByDistance(mMasterGroup.mNode,_targets)
                    _scale = mc.scaleConstraint(_targets,mMasterGroup.mNode,maintainOffset = True)#Point contraint loc to the object
                    CONSTRAINT.set_weightsByDistance(_scale[0],_vList)                
                    ml_ikScaleTargets.append(mSegMidIK)
                    _targets = [mHandle.mNode for mHandle in ml_ikScaleTargets]

                for mJnt in ml_ikJoints[1:-1]:
                    _vList = DIST.get_normalizedWeightsByDistance(mJnt.mNode,_targets)
                    _scale = mc.scaleConstraint(_targets,mJnt.mNode,maintainOffset = True)#Point contraint loc to the object
                    CONSTRAINT.set_weightsByDistance(_scale[0],_vList)
                
                for mJnt in ml_ikJoints[1:]:
                    mJnt.p_parent = mIKGroup
                    mJnt.segmentScaleCompensate = False
                    
                for mJnt in ml_blendJoints:
                    mJnt.segmentScaleCompensate = False
                    if mJnt == ml_blendJoints[0]:
                        continue
                    mJnt.p_parent = ml_blendJoints[0].p_parent
                
                
            else:
                RIGCONSTRAINT.blendChainsBy(ml_fkJoints,ml_ikJoints,ml_blendJoints,
                                            driver = mPlug_FKIK.p_combinedName,
                                            l_constraints=['point','orient'])
        

        #cgmGEN.func_snapShot(vars())
        return    
    except Exception,err:cgmGEN.cgmException(Exception,err)

#@cgmGEN.Timer
def rig_matchSetup(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_matchSetup'.format(_short)
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug(self)        
        mBlock = self.mBlock
        mRigNull = self.mRigNull
        mRootParent = self.mDeformNull
        mControlIK = mRigNull.controlIK
        mSettings = mRigNull.settings
        
        ml_rigJoints = mRigNull.msgList_get('rigJoints')
        ml_fkJoints = mRigNull.msgList_get('fkJoints')
        ml_blendJoints = mRigNull.msgList_get('blendJoints')
        ml_ikJoints = mRigNull.msgList_get('ikJoints')
        
        if not ml_ikJoints:
            return log.warning("|{0}| >> No Ik joints. Can't setup match".format(_str_func))
        
        len_fk = len(ml_fkJoints)
        len_ik = len(ml_ikJoints)
        len_blend = len(ml_blendJoints)
        
        if len_blend != len_ik and len_blend != len_fk:
            raise ValueError,"|{0}| >> All chains must equal length. fk:{1} | ik:{2} | blend:{2}".format(_str_func,len_fk,len_ik,len_blend)
        
        cgmGEN.func_snapShot(vars())
        
        mDynSwitch = mBlock.atRigModule('get_dynSwitch')
        _jointOrientation = self.d_orientation['str']
        
        
        
        #>>> FK to IK ==================================================================
        log.debug("|{0}| >> fk to ik...".format(_str_func))
        mMatch_FKtoIK = cgmRIGMETA.cgmDynamicMatch(dynObject=mControlIK,
                                                   dynPrefix = "FKtoIK",
                                                   dynMatchTargets = ml_blendJoints[-1])
        mMatch_FKtoIK.addPrematchData({'spin':0})
        
        
        
        
        
        #>>> IK to FK ==================================================================
        log.debug("|{0}| >> ik to fk...".format(_str_func))
        ml_fkMatchers = []
        for i,mObj in enumerate(ml_fkJoints):
            mMatcher = cgmRIGMETA.cgmDynamicMatch(dynObject=mObj,
                                                 dynPrefix = "IKtoFK",
                                                 dynMatchTargets = ml_blendJoints[i])        
            ml_fkMatchers.append(mMatcher)
            
        #>>> IK to FK ==================================================================
        log.debug("|{0}| >> Registration...".format(_str_func))
        
        mDynSwitch.addSwitch('snapToFK',"{0}.FKIK".format(mSettings.mNode),#[mSettings.mNode,'FKIK'],
                             0,
                             ml_fkMatchers)
        
        mDynSwitch.addSwitch('snapToIK',"{0}.FKIK".format(mSettings.mNode),#[mSettings.mNode,'FKIK'],
                             1,
                             [mMatch_FKtoIK])        
        
    except Exception,err:cgmGEN.cgmException(Exception,err)
    
def rig_cleanUp(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_neckSegment'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug(self)
    
    mRigNull = self.mRigNull
    mSettings = mRigNull.settings
    mRoot = mRigNull.rigRoot
    if not mRoot.hasAttr('cgmAlias'):
        mRoot.addAttr('cgmAlias','root')
    mBlock = self.mBlock
    
    mRootParent = self.mDeformNull
    mMasterControl= self.d_module['mMasterControl']
    mMasterDeformGroup= self.d_module['mMasterDeformGroup']    
    mMasterNull = self.d_module['mMasterNull']
    mModuleParent = self.d_module['mModuleParent']
    mPlug_globalScale = self.d_module['mPlug_globalScale']
    
    #if not self.mConstrainNull.hasAttr('cgmAlias'):
        #self.mConstrainNull.addAttr('cgmAlias','{0}_rootNull'.format(self.d_module['partName']))
    
    mAttachDriver = self.md_dynTargetsParent['attachDriver']
    if not mAttachDriver.hasAttr('cgmAlias'):
        mAttachDriver.addAttr('cgmAlias','{0}_rootDriver'.format(self.d_module['partName']))    
    
    #>>  DynParentGroups - Register parents for various controls ============================================
    ml_baseDynParents = []
    ml_endDynParents = self.ml_dynParentsAbove + self.ml_dynEndParents# + [mRoot]
    ml_ikDynParents = []
    
    """
    ml_baseDynParents = []
    ml_endDynParents = [mRoot,mMasterNull.puppetSpaceObjectsGroup, mMasterNull.worldSpaceObjectsGroup]
    
    if mModuleParent:
        mi_parentRigNull = mModuleParent.rigNull
        if mi_parentRigNull.getMessage('rigRoot'):
            ml_baseDynParents.append( mi_parentRigNull.rigRoot )        
        if mi_parentRigNull.getMessage('controlIK'):
            ml_baseDynParents.append( mi_parentRigNull.controlIK )	    
        if mi_parentRigNull.getMessage('controlIKBase'):
            ml_baseDynParents.append( mi_parentRigNull.controlIKBase )
        ml_parentRigJoints =  mi_parentRigNull.msgList_get('rigJoints')
        if ml_parentRigJoints:
            ml_used = []
            for mJnt in ml_parentRigJoints:
                if mJnt in ml_used:continue
                if mJnt in [ml_parentRigJoints[0],ml_parentRigJoints[-1]]:
                    ml_baseDynParents.append( mJnt.masterGroup)
                    ml_used.append(mJnt)"""
                    
                    
    #...Root controls ========================================================================================
    log.debug("|{0}| >>  Root: {1}".format(_str_func,mRoot))
    
    ml_targetDynParents = [self.md_dynTargetsParent['attachDriver']]
        
    if not mRoot.hasAttr('cgmAlias'):
        mRoot.addAttr('cgmAlias','{0}_root'.format(self.d_module['partName']))
        
    ml_targetDynParents.extend(self.ml_dynEndParents)
    mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mRoot.mNode,dynMode=0)
    ml_targetDynParents.extend(mRoot.msgList_get('spacePivots',asMeta = True))

    log.debug("|{0}| >>  Root Targets...".format(_str_func,mRoot))
    pprint.pprint(ml_targetDynParents)
    
    for mTar in ml_targetDynParents:
        mDynGroup.addDynParent(mTar)
    mDynGroup.rebuild()
    #mDynGroup.dynFollow.p_parent = self.mConstrainNull    
    
    ml_baseDynParents.append(mRoot)
    
    """
    mParent = mRoot.getParent(asMeta=True)
    ml_targetDynParents = []

    if not mParent.hasAttr('cgmAlias'):
        mParent.addAttr('cgmAlias',self.d_module['partName'] + 'base')
    ml_targetDynParents.append(mParent)    
    
    ml_targetDynParents.extend(ml_baseDynParents + ml_endDynParents)

    mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mRoot.mNode,dynMode=2)
    #mDynGroup.dynMode = 2

    for mTar in ml_targetDynParents:
        mDynGroup.addDynParent(mTar)
    mDynGroup.rebuild()
    mDynGroup.dynFollow.p_parent = self.mDeformNull"""
    
    #...ik controls ==================================================================================
    log.debug("|{0}| >>  IK Handles ... ".format(_str_func))                
    
    ml_ikControls = []
    mControlIK = mRigNull.getMessage('controlIK')
    
    if mControlIK:
        ml_ikControls.append(mRigNull.controlIK)
    if mRigNull.getMessage('controlIKBase'):
        ml_ikControls.append(mRigNull.controlIKBase)
        
    for mHandle in ml_ikControls:
        log.debug("|{0}| >>  IK Handle: {1}".format(_str_func,mHandle))
        
        ml_targetDynParents = ml_baseDynParents + [self.md_dynTargetsParent['attachDriver']] + ml_endDynParents
        
        ml_targetDynParents.append(self.md_dynTargetsParent['world'])
        ml_targetDynParents.extend(mHandle.msgList_get('spacePivots',asMeta = True))
    
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mHandle,dynMode=0)
        #mDynGroup.dynMode = 2
    
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        mDynGroup.rebuild()
        #mDynGroup.dynFollow.p_parent = self.mConstrainNull
        
    log.debug("|{0}| >>  IK targets...".format(_str_func))
    pprint.pprint(ml_targetDynParents)        
    
    log.debug(cgmGEN._str_subLine)
              
    
    if mRigNull.getMessage('controlIKMid'):
        log.debug("|{0}| >>  IK Mid Handle ... ".format(_str_func))                
        mHandle = mRigNull.controlIKMid
        
        mParent = mHandle.masterGroup.getParent(asMeta=True)
        ml_targetDynParents = []
    
        if not mParent.hasAttr('cgmAlias'):
            mParent.addAttr('cgmAlias','midIKBase')
        
        mPivotResultDriver = mRigNull.getMessage('pivotResultDriver',asMeta=True)
        if mPivotResultDriver:
            mPivotResultDriver = mPivotResultDriver[0]
        ml_targetDynParents = [mPivotResultDriver,mControlIK,mParent]
        
        ml_targetDynParents.extend(ml_baseDynParents + ml_endDynParents)
        #ml_targetDynParents.extend(mHandle.msgList_get('spacePivots',asMeta = True))
    
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mHandle,dynMode=0)
        #mDynGroup.dynMode = 2
    
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        mDynGroup.rebuild()
        #mDynGroup.dynFollow.p_parent = self.mConstrainNull
        
        log.debug("|{0}| >>  IK Mid targets...".format(_str_func,mRoot))
        pprint.pprint(ml_targetDynParents)                
        log.debug(cgmGEN._str_subLine)    
    
    
    """
    #...Ik controls ========================================================================================
    ml_ikControls = []
    mControlIK = mRigNull.getMessage('controlIK')
    
    if mControlIK:
        ml_ikControls.append(mRigNull.controlIK)
    if mRigNull.getMessage('controlIKBase'):
        ml_ikControls.append(mRigNull.controlIKBase)
        
    for mHandle in ml_ikControls:
        log.debug("|{0}| >>  IK Handle: {1}".format(_str_func,mHandle))                
        
        mParent = mHandle.getParent(asMeta=True)
        ml_targetDynParents = []
    
        if not mParent.hasAttr('cgmAlias'):
            mParent.addAttr('cgmAlias','conIK_base')
        ml_targetDynParents.append(mParent)    
        
        ml_targetDynParents.extend(ml_baseDynParents + ml_endDynParents)
        ml_targetDynParents.extend(mHandle.msgList_get('spacePivots',asMeta = True))
    
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mHandle,dynMode=2)
        #mDynGroup.dynMode = 2
    
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        mDynGroup.rebuild()
        mDynGroup.dynFollow.p_parent = self.mDeformNull"""
    
    
    #...rigjoints ============================================================================================
    if mBlock.spaceSwitch_direct:
        log.debug("|{0}| >>  Direct...".format(_str_func))                
        for i,mObj in enumerate(mRigNull.msgList_get('rigJoints')):
            log.debug("|{0}| >>  Direct: {1}".format(_str_func,mObj))                        
            ml_targetDynParents = copy.copy(ml_baseDynParents)
            ml_targetDynParents.extend(mObj.msgList_get('spacePivots',asMeta=True) or [])
            
            mParent = mObj.masterGroup.getParent(asMeta=True)
            if not mParent.hasAttr('cgmAlias'):
                mParent.addAttr('cgmAlias','{0}_rig{1}_base'.format(mObj.cgmName,i))
            ml_targetDynParents.insert(0,mParent)
            
            ml_targetDynParents.extend(ml_endDynParents)
            
            mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mObj.mNode)
            mDynGroup.dynMode = 2
            
            for mTar in ml_targetDynParents:
                mDynGroup.addDynParent(mTar)
            
            mDynGroup.rebuild()
            
            mDynGroup.dynFollow.p_parent = mRoot
    
    #...fk controls ============================================================================================
    log.debug("|{0}| >>  FK...".format(_str_func)+'-'*80)                
    ml_fkJoints = self.mRigNull.msgList_get('fkJoints')
    
    for i,mObj in enumerate(ml_fkJoints):
        if i :
            continue
        if not mObj.getMessage('masterGroup'):
            log.debug("|{0}| >>  Lacks masterGroup: {1}".format(_str_func,mObj))            
            continue
        log.debug("|{0}| >>  FK: {1}".format(_str_func,mObj))
        ml_targetDynParents = copy.copy(ml_baseDynParents)
        ml_targetDynParents.append(self.md_dynTargetsParent['attachDriver'])
        
        mParent = mObj.masterGroup.getParent(asMeta=True)
        if not mParent.hasAttr('cgmAlias'):
            mParent.addAttr('cgmAlias','{0}_base'.format(mObj.p_nameBase))
            
        if i == 0:
            ml_targetDynParents.append(mParent)
            _mode = 2            
        else:
            ml_targetDynParents.insert(0,mParent)
            _mode = 1
        
        ml_targetDynParents.extend(ml_endDynParents)
        ml_targetDynParents.extend(mObj.msgList_get('spacePivots',asMeta = True))
    
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mObj.mNode, dynMode=_mode)# dynParents=ml_targetDynParents)
        #mDynGroup.dynMode = 2
    
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        mDynGroup.rebuild()

        if i == 0:
            mDynGroup.dynFollow.p_parent = mRoot    
        
        log.debug("|{0}| >>  FK targets: {1}...".format(_str_func,mObj))
        pprint.pprint(ml_targetDynParents)                
        log.debug(cgmGEN._str_subLine)    
    
    #Settings =================================================================================
    log.debug("|{0}| >> Settings...".format(_str_func))
    mSettings.visRoot = 0
    mSettings.visDirect = 0
    
    
    ml_handleJoints = mRigNull.msgList_get('handleJoints')
    if ml_handleJoints:
        ATTR.set_default(ml_handleJoints[-1].mNode, 'followRoot', 1.0)
        ml_handleJoints[-1].followRoot = 1.0
        
        
    if mSettings.hasAttr('FKIK'):
        ATTR.set_default(mSettings.mNode, 'FKIK', 1.0)
        mSettings.FKIK = 1.0
    
    #Lock and hide =================================================================================
    ml_controls = mRigNull.msgList_get('controlsAll')
    
    for mCtrl in ml_controls:
        if mCtrl.hasAttr('radius'):
            ATTR.set_hidden(mCtrl.mNode,'radius',True)
        
        if mCtrl.getMessage('masterGroup'):
            mCtrl.masterGroup.setAttrFlags()
    
    if not mBlock.scaleSetup:
        log.debug("|{0}| >> No scale".format(_str_func))
        for mCtrl in ml_controls:
            ATTR.set_standardFlags(mCtrl.mNode, ['scale'])
    else:
        log.debug("|{0}| >>  ScaleSetup...".format(_str_func))
        
        #Start End
        
    
    
    
    
    #Close out ========================================================================================
    mBlock.blockState = 'rig'
    mRigNull.version = self.d_block['buildVersion']
    #cgmGEN.func_snapShot(vars())
    return


def build_proxyMesh(self, forceNew = True,  puppetMeshMode = False ):
    """
    Build our proxyMesh
    """
    _short = self.d_block['shortName']
    _str_func = '[{0}] > build_proxyMesh'.format(_short)
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug(self)
    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mSettings = mRigNull.settings
    mPuppetSettings = self.d_module['mMasterControl'].controlSettings
    
    directProxy = mBlock.proxyDirect
    
    _side = BLOCKUTILS.get_side(self.mBlock)
    ml_proxy = []
    
    ml_rigJoints = mRigNull.msgList_get('rigJoints',asMeta = True)
    if not ml_rigJoints:
        raise ValueError,"No rigJoints connected"
    
    #>> If proxyMesh there, delete ------------------------------------------------------------------------- 
    if puppetMeshMode:
        _bfr = mRigNull.msgList_get('puppetProxyMesh',asMeta=True)
        if _bfr:
            log.debug("|{0}| >> puppetProxyMesh detected...".format(_str_func))            
            if forceNew:
                log.debug("|{0}| >> force new...".format(_str_func))                            
                mc.delete([mObj.mNode for mObj in _bfr])
            else:
                return _bfr        
    else:
        _bfr = mRigNull.msgList_get('proxyMesh',asMeta=True)
        if _bfr:
            log.debug("|{0}| >> proxyMesh detected...".format(_str_func))            
            if forceNew:
                log.debug("|{0}| >> force new...".format(_str_func))                            
                mc.delete([mObj.mNode for mObj in _bfr])
            else:
                return _bfr
        
    # Create ---------------------------------------------------------------------------
    ml_segProxy = cgmMeta.validateObjListArg(self.atBuilderUtils('mesh_proxyCreate', ml_rigJoints,firstToStart=True),'cgmObject')
    
    
    if directProxy:
        _settings = self.mRigNull.settings.mNode
        log.debug("|{0}| >> directProxy... ".format(_str_func))    
    
    if puppetMeshMode:
        log.debug("|{0}| >> puppetMesh setup... ".format(_str_func))
        ml_moduleJoints = mRigNull.msgList_get('moduleJoints')
        
        for i,mGeo in enumerate(ml_segProxy):
            log.debug("{0} : {1}".format(mGeo, ml_moduleJoints[i]))
            mGeo.parent = ml_moduleJoints[i]
            mGeo.doStore('cgmName',self.d_module['partName'])
            mGeo.addAttr('cgmIterator',i+1)
            mGeo.addAttr('cgmType','proxyPuppetGeo')
            mGeo.doName()
            
        mRigNull.msgList_connect('puppetProxyMesh', ml_segProxy)
        return ml_segProxy
        
    for i,mGeo in enumerate(ml_segProxy):
        mGeo.parent = ml_rigJoints[i]
        ATTR.copy_to(ml_rigJoints[0].mNode,'cgmName',mGeo.mNode,driven = 'target')
        mGeo.addAttr('cgmIterator',i+1)
        mGeo.addAttr('cgmType','proxyGeo')
        mGeo.doName()
        
        if directProxy:
            CORERIG.shapeParent_in_place(ml_rigJoints[i].mNode,mGeo.mNode,True,True)
            CORERIG.colorControl(ml_rigJoints[i].mNode,_side,'main',directProxy=True)
            
            for mShape in ml_rigJoints[i].getShapes(asMeta=True):
                ATTR.connect("{0}.visDirect".format(_settings), "{0}.overrideVisibility".format(mShape.mNode))
            
    
    for mProxy in ml_segProxy:
        CORERIG.colorControl(mProxy.mNode,_side,'main',transparent=False,proxy=True)
        
        mc.makeIdentity(mProxy.mNode, apply = True, t=1, r=1,s=1,n=0,pn=1)

        #Vis connect -----------------------------------------------------------------------
        mProxy.overrideEnabled = 1
        ATTR.connect("{0}.proxyVis".format(mPuppetSettings.mNode),"{0}.visibility".format(mProxy.mNode) )
        ATTR.connect("{0}.proxyLock".format(mPuppetSettings.mNode),"{0}.overrideDisplayType".format(mProxy.mNode) )        
        for mShape in mProxy.getShapes(asMeta=1):
            str_shape = mShape.mNode
            mShape.overrideEnabled = 0
            ATTR.connect("{0}.proxyLock".format(mPuppetSettings.mNode),"{0}.overrideDisplayTypes".format(str_shape) )
        
    mRigNull.msgList_connect('proxyMesh', ml_segProxy)





















