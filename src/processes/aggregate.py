from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.PyQt import uic
from qgis.utils import iface

from . import processing


def create_selected_aggregate_feature(aggregate_layer, aggregate_name_field):
    """
    選択した地物で一時レイヤを生成する

    Args:
        aggregate_layer(QgsVectorLayer): 集計対象ポリゴン

    Returns:
        vlyr(QgsVectorLayer): 選択地物の一時レイヤ
    """
    # 選択地物のみを対象としてジオメトリの修復を実行する
    fix_aggregate_layer = processing.fix_selected_geometry(aggregate_layer)
    aggregate_layer_features = fix_aggregate_layer.getFeatures()

    # 空のベクタレイヤを作成
    aggregate_layer_crs = fix_aggregate_layer.crs().authid()
    vlyr = QgsVectorLayer(f'Polygon?crs={aggregate_layer_crs}',
                            '集計結果',
                            'memory')
    vlyr_provider = vlyr.dataProvider()

    # フィールドをセット
    attribute_name = [
        QgsField("id", QVariant.Int),
        QgsField(aggregate_name_field, QVariant.String),
        QgsField("面積", QVariant.Double, prec=1, len=20)
    ]
    vlyr_provider.addAttributes(attribute_name)
    vlyr.updateFields()

    for ftr in aggregate_layer_features:
        # QgsFeatureを作成
        qgs_feature = QgsFeature()
        # 属性の追加
        attributes = [
            ftr.id(),
            ftr.attribute(aggregate_name_field),
            ftr.geometry().area()
        ]
        qgs_feature.setAttributes(attributes)
        # ジオメトリを追加
        qgs_feature.setGeometry(ftr.geometry())
        # QgsFeatureを一時レイヤに追加
        vlyr_provider.addFeature(qgs_feature)

    # 集計ポリゴンの選択解除
    aggregate_layer.removeSelection()

    return vlyr

def run_aggregate(
        aggregate_layer,
        aggregate_polygon,
        aggregate_name_field,
        tmp_storage_layer,
        tmp_storage_name_fieldname,
        tmp_storage_area_fieldname,
        building_layer
        ):
    """
    集計処理の実行

    Args:
        None

    Returns:
        vlayer_join_tmp_storage(QgsVectorLayer): 集計結果のレイヤ
    """
    # 選択ポリゴン内のポイント・必要なフィールドを抽出
    extracted_building_pnts = processing.intersect(
        building_layer,
        ['T_Area', 'Flam_out', 'Noflam_out', 'Bld_Str', 'Cdst_Dmg', 'Hdst_Dmg', 'Prob_Burn', 'All_Out'],
        aggregate_polygon,
        ['id', aggregate_name_field]
    )

    extracted_tmp_storage_pnts = processing.intersect(
        tmp_storage_layer,
        [tmp_storage_name_fieldname, tmp_storage_area_fieldname],
        aggregate_polygon,
        ['id', aggregate_name_field]
    )

    # 町丁目単位で集計
    aggregated_building_pnts = processing.aggregate(extracted_building_pnts, [
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Bld_Str"=601', 'length': 20, 'name': '建物棟数（木造）',
            'precision': 0, 'type': 4},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Bld_Str"=610', 'length': 20, 'name': '建物棟数（非木造）',
            'precision': 0, 'type': 4},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Bld_Str">0', 'length': 20, 'name': '建物棟数（合計）',
            'precision': 0, 'type': 4},
        {'aggregate': 'sum', 'delimiter': '', 'input': '( "Bld_Str" = 601 ) * "Cdst_Dmg" ', 'length': 20,
            'name': '建物被害想定（木造：全壊）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '( "Bld_Str" = 601 ) * "Hdst_Dmg" ', 'length': 20,
            'name': '建物被害想定（木造：半壊）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '( "Bld_Str" = 601 ) * "Prob_Burn" ', 'length': 20,
            'name': '建物被害想定（木造：焼失）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '( "Bld_Str" = 610 ) * "Cdst_Dmg" ', 'length': 20,
            'name': '建物被害想定（非木造：全壊）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '( "Bld_Str" = 610 ) * "Hdst_Dmg" ', 'length': 20,
            'name': '建物被害想定（非木造：半壊）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '( "Bld_Str" = 610 ) * "Prob_Burn" ', 'length': 20,
            'name': '建物被害想定（非木造：焼失）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Cdst_Dmg"', 'length': 20,
            'name': '建物被害想定（合計：全壊）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Hdst_Dmg"', 'length': 20,
            'name': '建物被害想定（合計：半壊）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Prob_Burn"', 'length': 20,
            'name': '建物被害想定（合計：焼失）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Flam_out"', 'length': 20,
            'name': '災害廃棄物の発生量（可燃系）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"Noflam_out"', 'length': 20,
            'name': '災害廃棄物の発生量（不燃系）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"All_Out"', 'length': 20,
            'name': '災害廃棄物の発生量（合計）', 'precision': 1, 'type': 6},
        {'aggregate': 'sum', 'delimiter': '', 'input': '"T_Area"', 'length': 20,
            'name': '仮置場必要面積', 'precision': 1, 'type': 6},
        {'aggregate': 'first_value', 'delimiter': ',', 'input': 'id', 'length': 20,
            'name': 'id', 'precision': 0, 'type': 4},
        {'aggregate': 'first_value', 'delimiter': ',', 'input': f'"{aggregate_name_field}"', 'length': 0,
            'name': aggregate_name_field, 'precision': 0, 'type': 10}],
                                                    'id')

    aggregated_tmp_storage_pnts = processing.aggregate(
        extracted_tmp_storage_pnts,
        [{'aggregate': 'concatenate', 'delimiter': ',', 'input': f'"{tmp_storage_name_fieldname}"', 'length': 0,
            'name': '仮置場名称',
            'precision': 0, 'type': 10},
            {'aggregate': 'sum', 'delimiter': ',', 'input': f'"{tmp_storage_area_fieldname}"', 'length': 20,
            'name': '仮置場概略有効面積',
            'precision': 1, 'type': 6},
            {'aggregate': 'first_value', 'delimiter': ',', 'input': '"id"', 'length': 20, 'name': 'id',
            'precision': 0, 'type': 4},
            {'aggregate': 'first_value', 'delimiter': ',', 'input': f'"{aggregate_name_field}"', 'length': 0,
            'name': aggregate_name_field,
            'precision': 0, 'type': 10}],
        'id')


    # idをキーとしてテーブル結合
    vlayer_join_buildings = processing.table_join(
        aggregate_polygon,
        'id',
        aggregated_building_pnts,
        'id',
        ['建物棟数（木造）', '建物棟数（非木造）', '建物棟数（合計）', '建物被害想定（木造：全壊）', '建物被害想定（木造：半壊）', '建物被害想定（木造：焼失）',
            '建物被害想定（非木造：全壊）', '建物被害想定（非木造：半壊）', '建物被害想定（非木造：焼失）', '建物被害想定（合計：全壊）',
            '建物被害想定（合計：半壊）', '建物被害想定（合計：焼失）', '災害廃棄物の発生量（可燃系）', '災害廃棄物の発生量（不燃系）',
            '災害廃棄物の発生量（合計）', '仮置場必要面積'],
    )

    vlayer_join_tmp_storage = processing.table_join(
        vlayer_join_buildings,
        'id',
        aggregated_tmp_storage_pnts,
        'id',
        ['仮置場名称', '仮置場概略有効面積']
    )
  
    # idカラムの削除
    vlayer_delete_id_column = processing.delete_column(vlayer_join_tmp_storage,['id'])

    # 属性の端数処理を行う
    features = vlayer_delete_id_column.getFeatures()

    field_list = ['面積', '建物被害想定（木造：全壊）', '建物被害想定（木造：半壊）', '建物被害想定（木造：焼失）',
                    '建物被害想定（非木造：全壊）', '建物被害想定（非木造：半壊）', '建物被害想定（非木造：焼失）', '建物被害想定（合計：全壊）',
                    '建物被害想定（合計：半壊）', '建物被害想定（合計：焼失）', '災害廃棄物の発生量（可燃系）', '災害廃棄物の発生量（不燃系）',
                    '災害廃棄物の発生量（合計）', '仮置場必要面積', '仮置場概略有効面積']

    vlayer_delete_id_column.startEditing()
    lyr_fields = vlayer_delete_id_column.fields()

    for feature in features:
        for field in field_list:
            field_idx = lyr_fields.indexOf(field)
            value = feature[field]
            # 値がNone（QVariant）の場合は処理をスキップ
            if type(value) == QVariant:
                continue
            round_value = round(value, 1)
            vlayer_delete_id_column.changeAttributeValue(feature.id(), field_idx, round_value)

    vlayer_delete_id_column.commitChanges()

    vlayer_delete_id_column.setName("集計結果")

    # 集計ポリゴンの真下にレイヤを追加する
    root = QgsProject.instance().layerTreeRoot()
    QgsProject.instance().addMapLayer(vlayer_delete_id_column, False)
    QgsLayerTreeUtils.insertLayerBelow(root, aggregate_layer, vlayer_delete_id_column)

    return vlayer_delete_id_column

def apply_symbology(aggregated_layer):
    """
    集計レイヤを定数でスタイリングをする

    Args:
        aggregated_layer(QgsVectorLayer): 集計レイヤ

    Returns:
        None
    """
    myRangeList = []

    symbol = QgsSymbol.defaultSymbol(aggregated_layer.geometryType())
    symbol.setColor(QColor("#fff9f9"))
    symbol.setOpacity(0.7)
    myRange = QgsRendererRange(0, 2000, symbol, '0-2000㎡')
    myRangeList.append(myRange)

    symbol = QgsSymbol.defaultSymbol(aggregated_layer.geometryType())
    symbol.setColor(QColor("#ffcccc"))
    symbol.setOpacity(0.7)
    myRange = QgsRendererRange(2000, 4000, symbol, '2000-4000㎡')
    myRangeList.append(myRange)

    symbol = QgsSymbol.defaultSymbol(aggregated_layer.geometryType())
    symbol.setColor(QColor("#ff9999"))
    symbol.setOpacity(0.7)
    myRange = QgsRendererRange(4000, 6000, symbol, '4000-6000㎡')
    myRangeList.append(myRange)

    symbol = QgsSymbol.defaultSymbol(aggregated_layer.geometryType())
    symbol.setColor(QColor("#ff6666"))
    symbol.setOpacity(0.7)
    myRange = QgsRendererRange(6000, 8000, symbol, '6000-8000㎡')
    myRangeList.append(myRange)

    symbol = QgsSymbol.defaultSymbol(aggregated_layer.geometryType())
    symbol.setColor(QColor("#ff3333"))
    symbol.setOpacity(0.7)
    myRange = QgsRendererRange(8000, 10000, symbol, '8000-10000㎡')
    myRangeList.append(myRange)

    symbol = QgsSymbol.defaultSymbol(aggregated_layer.geometryType())
    symbol.setColor(QColor("#ff0000"))
    symbol.setOpacity(0.7)
    myRange = QgsRendererRange(10000, 9999999, symbol, '10000㎡-')
    myRangeList.append(myRange)

    myRenderer = QgsGraduatedSymbolRenderer('coalesce("仮置場必要面積",0)', myRangeList)
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Custom)

    aggregated_layer.setRenderer(myRenderer)