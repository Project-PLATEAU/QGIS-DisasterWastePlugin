"""
/***************************************************************************
 DisasterWastePlugin
                                 A QGIS plugin
 Disaster Waste calculation tool for QGIS
                              -------------------
        begin                : 2023-03-01
        git sha              : $Format:%H$
        copyright            : (C) 2023 by MLIT.
        email                : 
        license              : GNU General Public License v2.0
 ***************************************************************************/
"""


def classFactory(iface):
    from .disaster_waste_plugin import DisasterWastePlugin
    return DisasterWastePlugin(iface)
