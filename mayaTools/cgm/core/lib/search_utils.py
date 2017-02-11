"""
------------------------------------------
search_utils: cgm.core.lib.search_utils
Author: Josh Burton
email: jjburton@cgmonks.com
Website : http://www.cgmonks.com
------------------------------------------

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
import maya.mel as mel
# From Red9 =============================================================

# From cgm ==============================================================
from cgm.core import cgm_General as cgmGen
from cgm.core.cgmPy import validateArgs as coreValid
reload(coreValid)
from cgm.core.lib import shared_data as coreShared
from cgm.core.lib import name_utils as NAME
from cgm.core.lib import attribute_utils as ATTR
from cgm.lib import attributes

from cgm.lib import lists
#>>> Utilities
#===================================================================   
is_shape = coreValid.is_shape
is_transform = coreValid.is_transform    
get_mayaType = coreValid.get_mayaType
def get_transform(node = None):
    """
    Get transform of given node
    
    :parameters:
        node(str): Object to check

    :returns
        status(bool)
    """   
    _str_func = 'is_transform'
    _node = coreValid.stringArg(node,False,_str_func) 
    
    if '.' in node:
        _buffer = node.split('.')[0]
    else:
        _buffer = node
        
    _buffer = mc.ls(_buffer, type = 'transform',long = True) or False
    if _buffer:
        return NAME.get_short(_buffer[0])
    else:
        _buffer = mc.listRelatives(node,parent=True,type='transform',fullPath = True) or False
    if _buffer:
        return NAME.get_short(_buffer[0])
    return False    

def get_tag(node = None, tag = None):
    """
    Get the info on a given node with a provided tag
    
    :parameters:
        node(str): Object to check

    :returns
        status(bool)
    """   
    _str_func = 'get_tag'
    _node = coreValid.stringArg(node,False,_str_func) 
    
    if (mc.objExists('%s.%s' %(_node,tag))) == True:
        messageQuery = (mc.attributeQuery (tag,node=_node,msg=True))
        if messageQuery == True:
            returnBuffer = attributes.returnMessageData(_node,tag,False)
            if not returnBuffer:
                return False
            elif coreValid.get_mayaType(returnBuffer[0]) == 'reference':
                if attributes.repairMessageToReferencedTarget(_node,tag):
                    return attributes.returnMessageData(_node,tag,False)[0]
                return returnBuffer[0]
            return returnBuffer[0]
        else:
            infoBuffer = mc.getAttr('%s.%s' % (_node,tag))
            if infoBuffer is not None and len(list(str(infoBuffer))) > 0:
                return infoBuffer
            else:
                return False
    else:
        return False    
    
def get_all_parents(node = None, shortNames = True):
    """
    Get all the parents of a given node where the last parent is the top of the heirarchy
    
    :parameters:
        node(str): Object to check
        shortNames(bool): Whether you just want short names or long

    :returns
        parents(list)
    """   
    _str_func = 'get_all_parents'
    _node = coreValid.stringArg(node,False,_str_func) 
    
    _l_parents = []
    tmpObj = node
    noParent = False
    while noParent == False:
        tmpParent = mc.listRelatives(tmpObj,allParents=True,fullPath=True)
        if tmpParent:
            if len(tmpParent) > 1:
                raise ValueError,"Resolve what to do with muliple parents...{0} | {1}".format(node,tmpParent)
            _l_parents.append(tmpParent[0])
            tmpObj = tmpParent[0]
        else:
            noParent = True
    if shortNames:
        return [NAME.get_short(o) for o in _l_parents]
    return _l_parents 

def get_timeline_dict():
    """
    Returns timeline info as a dictionary
    
    :returns
        dict :: currentTime,sceneStart,sceneEnd,rangeStart,rangeEnd
    """   
    _str_func = 'get_timeline_dict'
    returnDict = {}
    returnDict['currentTime'] = mc.currentTime(q=True)
    returnDict['sceneStart'] = mc.playbackOptions(q=True,animationStartTime=True)
    returnDict['sceneEnd'] = mc.playbackOptions(q=True,animationEndTime=True)
    returnDict['rangeStart'] = mc.playbackOptions(q=True,min=True)
    returnDict['rangeEnd'] = mc.playbackOptions(q=True,max=True)

    return returnDict    

def get_key_indices_from(node = None, mode = 'all'):
    """
    Return a list of the time indexes of the keyframes on an object

    :parameters:
        node(str): What you want to get the keys of
        mode(str):
            all -- Every key
            next --
            previous -- 
            forward --
            back --
    
    :returns
        list of keys(list)
    """ 
    _str_func = 'get_key_indices'
    
    if not ATTR.get_keyed(node):
        return []
    
    initialTimeState = mc.currentTime(q=True)
    keyFrames = []
    
    if mode == 'next':
        _key = mc.findKeyframe(node,which = 'next',an='objects')
        if _key > initialTimeState:
            return [_key]
        return []
    elif mode == 'forward':
        lastKey = mc.findKeyframe(node,which = 'last',an='objects')
        mc.currentTime(initialTimeState-1)        
        while mc.currentTime(q=True) != lastKey:
            keyBuffer = mc.findKeyframe(node,which = 'next',an='objects')
            keyFrames.append(keyBuffer)
            mc.currentTime(keyBuffer)
        keyFrames.append(lastKey) 
    elif mode in ['previous','back']:
        firstKey = mc.findKeyframe(node,which = 'first',an='objects')
        lastKey = mc.findKeyframe(node,which = 'last',an='objects')        
        mc.currentTime(firstKey-1)
        while mc.currentTime(q=True) != lastKey:
            if mc.currentTime(q=True) >= initialTimeState:
                log.debug('higher: {0}'.format(mc.currentTime(q=True)))
                break
            keyBuffer = mc.findKeyframe(node,which = 'next',an='objects')
            keyFrames.append(keyBuffer)
            mc.currentTime(keyBuffer)
        if mode == 'previous' and keyFrames:
            keyFrames = [keyFrames[-1]]

        
    elif mode == 'all':
        firstKey = mc.findKeyframe(node,which = 'first',an='objects')
        lastKey = mc.findKeyframe(node,which = 'last',an='objects')
    
        keyFrames.append(firstKey)
        mc.currentTime(firstKey-1)
        while mc.currentTime(q=True) != lastKey:
            keyBuffer = mc.findKeyframe(node,which = 'next',an='objects')
            keyFrames.append(keyBuffer)
            mc.currentTime(keyBuffer)
    
        keyFrames.append(lastKey)
    
        # Put the time back where we found it
        mc.currentTime(initialTimeState)
    else:
        raise ValueError,"Unknown mode: {0}".format(mode)
    
    mc.currentTime(initialTimeState)
    return lists.returnListNoDuplicates(keyFrames)
    

def get_selectedFromChannelBox(attributesOnly = False):
    """ 
    Returns a list of selected object attributes from the channel box
    
    :parameters:
        attributesOnly(bool): Whether you want
        
    Keyword arguments:
    returnRaw() -- whether you just want channels or objects combined with selected attributes

    """    
    _sel = mc.ls(sl=True)
    ChannelBoxName = mel.eval('$tmp = $gChannelBoxName');

    sma = mc.channelBox(ChannelBoxName, query=True, sma=True)
    ssa = mc.channelBox(ChannelBoxName, query=True, ssa=True)
    sha = mc.channelBox(ChannelBoxName, query=True, sha=True)
    soa = mc.channelBox(ChannelBoxName, query=True, soa=True)


    channels = []
    if sma:
        channels.extend(sma)
    if ssa:
        channels.extend(ssa)
    if sha:
        channels.extend(sha)
    if soa:
        channels.extend(soa)
    
    if channels and _sel:
        _channels_long = []
        for c in channels:
            _channels_long.append(ATTR.get_nameLong(_sel[0],c))
            
        if attributesOnly:
            return _channels_long
        else:
            _res = []
            for item in _sel:
                for attr in _channels_long:
                    _res.append("{0}.{1}".format(item,attr))
            return _res
    return False 




    
    