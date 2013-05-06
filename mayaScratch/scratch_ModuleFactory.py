import cgm.core
cgm.core._reload()
import maya.cmds as mc

from cgm.core import cgm_Meta as cgmMeta
from cgm.core import cgm_PuppetMeta as cgmPM
import Red9.core.Red9_Meta as r9Meta
from cgm.core.rigger import ModuleFactory as mFactory
from cgm.core.rigger import TemplateFactory as tFactory
from cgm.core.rigger import JointFactory as jFactory

from cgm.core import cgm_PuppetMeta as cgmPM

reload(mFactory)
reload(tFactory)
reload(jFactory)

from cgm.core.classes import SnapFactory as Snap
reload(Snap)
from cgm.core.rigger import ModuleControlFactory as mControlFactory
reload(mControlFactory)
from cgm.lib import search
obj = mc.ls(sl=True)[0] or False
obj = ''
objList = []

#>>> Modules
#=======================================================
m1 = r9Meta.MetaClass('spine_part')
m1.setState('skeleton')
m1.getPartNameBase()
m1.rigNull.getMessage('rigJoints',False)
len( m1.rigNull.getMessage('rigJoints',False) )
len( m1.rigNull.getMessage('skinJoints',False) )

for o in m1.rigNull.getMessage('rigJoints',False):
    cgmMeta.cgmObject(o).getConstraintsTo()
    
for o in m1.rigNull.getMessage('skinJoints',False):
    cgmMeta.cgmObject(o).getConstraintsTo()

m1.rigNull.skinJoints[0].getConstraintsTo()
cgmMeta.cgmObject().isConstrainedBy()
reload(mFactory)
m1.getState()
mFactory.isRigConnected(m1)
mFactory.isRigged(m1)
mFactory.rigConnect(m1)
mFactory.rigDisconnect(m1)
mFactory.doRig(m1)

mFactory.deleteRig(m1)


