# QGIS-API
from qgis.PyQt import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import iface
import processing


def intersect(input_lyr: QgsVectorLayer, input_fields: list, overlay_lyr: QgsVectorLayer, overlay_fields: list):
    return processing.run("qgis:intersection",
                          {'INPUT': input_lyr,
                           'INPUT_FIELDS': input_fields,
                           'OVERLAY': overlay_lyr,
                           'OVERLAY_FIELDS': overlay_fields,
                           'OVERLAY_FIELDS_PREFIX': '',
                           'OUTPUT': 'TEMPORARY_OUTPUT'
                           }
                          )["OUTPUT"]


def fix_selected_geometry(input_lyr: QgsVectorLayer):
    return processing.run("native:fixgeometries",
                                        {'INPUT':QgsProcessingFeatureSourceDefinition(input_lyr.id(), True),
                                        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

def aggregate(input_lyr: QgsVectorLayer, aggregates: list, group_by: str):
    return processing.run("qgis:aggregate", {'AGGREGATES': aggregates, 'GROUP_BY': f'"{group_by}"',
                                             'INPUT': input_lyr,
                                             'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

def table_join(base_layer: QgsVectorLayer, base_field: str, layer_to_join: QgsVectorLayer, join_field: str,
               fields_to_copy: list):
    return processing.run("native:joinattributestable",
                          {'DISCARD_NONMATCHING': False,
                           'FIELD': base_field,
                           'FIELDS_TO_COPY': fields_to_copy,
                           'FIELD_2': join_field,
                           'INPUT': base_layer,
                           'INPUT_2': layer_to_join,
                           'METHOD': 1,
                           'OUTPUT': 'TEMPORARY_OUTPUT', 'PREFIX': ''})['OUTPUT']

def delete_column(input_lyr: QgsVectorLayer, delete_column: list):
    return processing.run("native:deletecolumn", 
                          {'INPUT': input_lyr,
                           'COLUMN': delete_column,
                           'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']