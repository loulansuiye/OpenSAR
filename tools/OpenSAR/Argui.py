from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys,os,re
import xml.etree.ElementTree as ET
import traceback
from Arxml import *

__all__ = ['ArgModule','ArgAction']

def Integer(cstr):
    cstr = str(cstr)
    try:
        if(cstr.find('0x')!=-1 or cstr.find('0X')!=-1):
            return int(cstr,16)
        else:
            return int(cstr,10)
    except:
        #print traceback.format_exc()
        return None
    
class ArgInput(QLineEdit):
    def __init__(self,key,arxml,root):
        assert(isinstance(root,ArgModule))
        self.key = key
        self.arxml = arxml
        self.root  = root
        
        super(QLineEdit,self).__init__(self.arxml.attrib(self.key))
        self.connect(self, SIGNAL('textChanged(QString)'),self.onTextChanged)
    def onTextChanged(self,text):
        reInput = re.compile(r'^(Text|Integer)')
        descriptor = self.arxml.getKeyDescriptor(self.key)
        
        type = reInput.search(descriptor).groups()[0]
        
        doUpdate = False
        if(text == 'TBD' or text == 'TB' or text == 'T' or text == '' or
           text == '0x' or text == '0X' or text == '0'):
            doUpdate = True
        elif(type == 'Text'):
            doUpdate = True
        elif(type == 'Integer'):
            reRange = re.compile(r'Range=(\w*)~(\w*)')
            if(reRange.search(descriptor)):
                print '>>>'
                min = Integer(reRange.search(descriptor).groups()[0])
                max = Integer(reRange.search(descriptor).groups()[1])
                var = Integer(text)
                
                if(var!=None and var>=min and var<=max):
                    doUpdate = True
            elif(Integer(text) != None):
                doUpdate = True
                
        
        if(doUpdate):
            self.arxml.attrib(self.key,text)
            if(self.key == 'Name'):
                self.root.onObjectNameChanged(text)
        else:
            self.setText(self.arxml.attrib(self.key))

class ArgSelect(QComboBox):
    def __init__(self,key,arxml,root):
        assert(isinstance(root,ArgModule))
        self.key = key
        self.arxml = arxml
        self.root  = root
        super(QComboBox,self).__init__()
        self.initItems()
        self.connect(self, SIGNAL('currentIndexChanged(QString)'),self.onTextChanged)
    def initItems(self):
        reSelect = re.compile(r'^(Enum|EnumRef|Boolean)')
        descriptor = self.arxml.getKeyDescriptor(self.key)
        type = reSelect.search(descriptor).groups()[0]
        if(type == 'Enum'):
            reList = re.compile(r'^Enum=\((.*)\)')
            list = reList.search(descriptor).groups()[0].split(',')
            self.addItems(QStringList(list))
        elif(type == 'Boolean'):
            self.addItems(QStringList(['True','False']))
        
        self.setCurrentIndex(self.findText(self.arxml.attrib(self.key)))
    def onTextChanged(self,text):
        self.arxml.attrib(self.key,text)        
        if(self.key == 'Name'):
            self.root.onObjectNameChanged(text)

def ArgWidget(key,arxml,root):
    reInput = re.compile(r'^Text|Integer')
    reSelect = re.compile(r'^Enum|EnumRef|Boolean')
    descriptor = arxml.getKeyDescriptor(key)
    if(reInput.search(descriptor)):
        return ArgInput(key,arxml,root)
    elif(reSelect.search(descriptor)):
        return ArgSelect(key,arxml,root)
    else:
        return QLineEdit('Type Error for %s'%(arxml.tag))

class ArgAction(QAction):
    def __init__(self,text,parent): 
        super(QAction,self).__init__(text,parent) 
        self.root =  parent
        self.connect(self,SIGNAL('triggered()'),self.onAction)
 
    def onAction(self):
        self.root.onAction(self.text())

class ArgObject(QTreeWidgetItem):
    def __init__(self,arxml,root,parent=None):  
        assert(isinstance(root,ArgModule))
        super(QTreeWidgetItem,self).__init__(parent)
        self.root =  root
        self.arxml = arxml
        self.setText(0,'%s %s'%(self.arxml.tag,self.arxml.attrib('Name')))
        
        for arx in self.arxml.childArxmls2():
            self.addChildArobj(ArgObject(arx,self.root,self))
        self.setExpanded(True)
        
    def toArxml(self):
        arxml = self.arxml.toArxml()
        for i in range(0,self.childCount()):
            arobj = self.child(i)
            assert(isinstance(arobj, ArgObject))
            arxml.append(arobj.toArxml())
        return arxml

    def addChildArobj(self,arobj):
        assert(isinstance(arobj, ArgObject))
        self.addChild(arobj)
        if(IsArxmlList(arobj.arxml)):
            pass
        else:
            if('TBD' == arobj.arxml.attrib('Name')):
                arobj.arxml.attrib('Name','%s%s'%(arobj.arxml.tag,self.childCount()))
                arobj.onObjectNameChanged(arobj.arxml.attrib('Name'))
        
    def onObjectNameChanged(self,text):
        assert(text == self.arxml.attrib('Name'))
        self.setText(0,'%s %s'%(self.arxml.tag,self.arxml.attrib('Name')))

    def onItemSelectionChanged(self):
        Index = 0
        for Descriptor in self.arxml.childDescriptors():
            already = False
            if(IsArxmlList(self.arxml)):
                # ok, it is a list things
                for I in range(0,self.childCount()):
                    tree = self.child(I)
                    if(tree.text(0) == Descriptor.tag):
                        already = True
                        break
            if(already == False): 
                self.root.actions[Index].setText('Add %s'%(Descriptor.tag))
                self.root.actions[Index].setDisabled(False)
                Index += 1
        if(self.parent() != None): # if parent is None, then it is top arobj, cann't be deleted
            self.root.actions[Index].setText('Delete %s'%(self.arxml.tag))
            self.root.actions[Index].setDisabled(False)
            Index += 1
        for i in range(Index,4):
            self.root.actions[i].setDisabled(True)
            
        self.root.showConfig(self.arxml)
        
    def onAction_Add(self,what,arxml=None):
        for Descriptor in self.arxml.childDescriptors():
            if(Descriptor.tag == what):
                if(IsArxmlList(self.arxml)):
                    max = self.arxml.getMaxChildAllowed()
                    if(max > self.childCount()):
                        self.addChildArobj(ArgObject(Arxml(Descriptor),self.root,self))
                    else:
                        print 'Error:Maximum %s for %s is %s!'%(what,self.arxml.tag,max)
                else:
                    # ok, by default this is list things
                    already = False
                    for I in range(0,self.childCount()):
                        arobj = self.child(I)
                        if(arobj.arxml.tag == Descriptor.tag):
                            already = True
                            break
                    if(already == False):
                        self.addChildArobj(ArgObject(Arxml(Descriptor),self.root,self))
                    else:
                        print 'Info: Only 1 %s is allowed for %s.'%(Descriptor.tag,self.arxml.tag)
                self.setExpanded(True)        

class ArgObjectTree(QTreeWidget):
    def __init__(self,arxml,parent=None):  
        assert(isinstance(parent,ArgModule))
        super(QTreeWidget,self).__init__(parent) 
        self.root  = parent
        self.arxml = arxml
        self.setHeaderLabel('%s'%(self.arxml.tag))
        for arxml in self.arxml.childArxmls():
            self.addTopLevelItem(ArgObject(arxml,self.root))
        self.connect(self, SIGNAL('itemSelectionChanged()'),self.itemSelectionChanged)
        self.setMaximumWidth(300)
        
    def onAction_Delete(self,what):
        arobj = self.currentItem()
        assert(isinstance(arobj,ArgObject))
        assert(arobj.arxml.tag == what)
        if(self.indexOfTopLevelItem(arobj) != -1):
            self.takeTopLevelItem(self.indexOfTopLevelItem(arobj))
        else:
            pObj = arobj.parent()
            pObj.takeChild(pObj.indexOfChild(arobj))
    def reloadArxml(self,arxml):
        for i in range(0,self.topLevelItemCount()):
            self.takeTopLevelItem(0)
        self.arxml = arxml
        for arxml in self.arxml.childArxmls2():
            arobj =ArgObject(arxml,self.root) 
            self.addTopLevelItem(arobj)

    def toArxml(self):
        arxml = self.arxml.toArxml()
        for i in range(0,self.topLevelItemCount()):
            arobj = self.topLevelItem(i)
            assert(isinstance(arobj, ArgObject))
            arxml.append(arobj.toArxml())
        return arxml
    def onAction(self,text):
        reAction = re.compile(r'(Add|Delete) (\w+)')
        action = reAction.search(text).groups()
        if(action[0] == 'Add'):
            arobj = self.currentItem()
            assert(isinstance(arobj,ArgObject))
            arobj.onAction_Add(action[1])
        elif(action[0] == 'Delete'):
            self.onAction_Delete(action[1])
       
    def itemSelectionChanged(self):
        arobj = self.currentItem()
        assert(isinstance(arobj,ArgObject))
        arobj.onItemSelectionChanged()
    
    def onObjectNameChanged(self,text):
        arobj = self.currentItem()
        assert(isinstance(arobj,ArgObject))
        arobj.onObjectNameChanged(text)

class ArgModule(QMainWindow):
    # TODO: actions = []
    # members declare here seems to be static 
    # that is the members can be accessed by all instance of class ArgModule
    # SO BETTER TO DECALRE MEMEBERS in __init__()
    def __init__(self,arxml,parent=None):
        self.actions = []
        super(QMainWindow,self).__init__(parent)
        self.tag = arxml.tag
        
        self.qSplitter = QSplitter(Qt.Horizontal,self)
        
        self.arobjTree = ArgObjectTree(arxml,self)
        self.wConfig  = QMainWindow()
        self.qSplitter.insertWidget(0,self.arobjTree)
        self.qSplitter.insertWidget(1,self.wConfig)
        
        self.setCentralWidget(self.qSplitter)
        self.creActions()
    
    def reloadArxml(self,arxml):
        self.arobjTree.reloadArxml(arxml)
    
    def toArxml(self):
        return self.arobjTree.toArxml()
    
    def showConfig(self,arxml):
        self.grid = QGridLayout()
        self.frame = QFrame()
        self.frame.setLayout(self.grid)
        if(arxml != None and IsArxmlList(arxml)==False):
            Row = 0
            for [key,value] in arxml.configuration.items():
                if(key == 'Name'): # put name as the first
                    K = QLabel(key)
                    V = ArgWidget(key,arxml,self)
                    self.grid.addWidget(K,Row,0)
                    self.grid.addWidget(V,Row,1)
                    Row += 1
            for [key,value] in arxml.configuration.items():
                if(key != 'Name'):
                    K = QLabel(key)
                    V = ArgWidget(key,arxml,self)
                    self.grid.addWidget(K,Row,0)
                    self.grid.addWidget(V,Row,1)
                    Row += 1
        self.wConfig.setCentralWidget(self.frame)
    def creActions(self):
        #  create 4 action
        for i in range(0,4):
            qAction=ArgAction(self.tr('Action%s'%(i)),self) 
            self.menuBar().addAction(qAction)
            qAction.setDisabled(True)
            self.actions.append(qAction)
            
    def onAction(self,text):
        self.arobjTree.onAction(text)
    
    def onObjectNameChanged(self,text):
        self.arobjTree.onObjectNameChanged(text)

if __name__ == '__main__':
    qtApp = QtGui.QApplication(sys.argv)
    if(os.name == 'nt'):
        qtApp.setFont(QFont('Consolas', 12)) 
    elif(os.name == 'posix'):
        qtApp.setFont(QFont('Monospace', 12))
    else:
        print('unKnown platform.')
    qtGui = ArgModule(Arxml(ET.parse('./easySAR.arxml').getroot().find('OS')))
    qtGui.show()
    qtApp.exec_()  