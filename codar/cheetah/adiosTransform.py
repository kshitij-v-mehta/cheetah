"""
Functions for parsing and editing the ADIOS xml file to enable variable transforms.
Transforms include compression and reduction. 'Transform' is an ADIOS specific term.

Not making this a class right now.
"""

import xml.etree.cElementTree as ET

def adiosXMLTransform(groupAndVarName, value, xmlFilepath):
    """
    Edit the ADIOS XML file to enable transform (compression/reduction) for a variable
    
    :param varName:     Name of the variable that will be transformed
    :param value:       Transform type (sz, zfp etc.)
    :param xmlFilepath: Full path of the adios xml file. This will be in the run directory.
    :return:            success or error. Return error if variable not found.
    """

    groupName = groupAndVarName.split(":")[0]
    varName = groupAndVarName.split(":")[1]


    tree = ET.parse(xmlFilepath)
    root = tree.getroot()

    tag = tree.find('adios-group[@name="%s"]/global-bounds/var[@name="%s"]' % (groupName, varName))
    tag.set('transform', value)
    tree.write(xmlFilepath)


#if __name__ == "__main__":
 #   adiosXMLTransform("heat:T", "sz", "/Users/kpu/vshare/scratch/heat_transfer.xml")