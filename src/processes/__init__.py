from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.PyQt import uic
from qgis.utils import iface

from . import aggregate, processing


def export_csv(export_layer):
    """
    対象レイヤのCSVをエクスポート

    Args:
        export_layer(QgsVectorLayer): 対象レイヤ

    Returns:
        None
    """
    filename = QFileDialog.getSaveFileName(None, "CSV出力", "", "CSV Files (*.csv)")
    if filename[0] == '':
        return
    QgsVectorFileWriter.writeAsVectorFormat(export_layer, filename[0], "shift-jis", driverName="CSV")
    QMessageBox.question(None, "確認", "CSVファイルを出力しました。", QMessageBox.Ok)

def create_printlayout(aggregated_layer, aggregated_summary, graph_png_path):
    """
    集計レイヤの印刷レイアウトの作成

    Args:
        aggregated_layer(QgsVectorLayer): 対象レイヤ
        aggregated_summary(Str): 集計サマリーテキスト
        graph_png_path(Str): 集計結果グラフのパス

    Returns:
        None
    """
    project = QgsProject.instance()
    manager = project.layoutManager()
    printlayout_name = "仮置場割当て結果"

    # プリントレイアウトがすでに作成されているか検証
    printlayout_list = [layout.name() for layout in manager.printLayouts()]
    if printlayout_name in printlayout_list:
        if QMessageBox.No == QMessageBox.question(
            None,
            "上書き確認",
            f'"{printlayout_name}"のレイアウトがプロジェクトに存在します、上書きしますか？',
            QMessageBox.Yes,
            QMessageBox.No,
        ):
            return
        project.layoutManager().removeLayout(manager.layoutByName(printlayout_name))

    # レイアウトの作成
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(printlayout_name)
    manager.addLayout(layout)

    # レイアウトをA4縦に設定
    pc = layout.pageCollection()
    pc.page(0).setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)

    # マップの作成
    map = QgsLayoutItemMap(layout)
    map.setRect(QRectF(10, 10, 10, 10))
    map.setFrameEnabled(True)

    # マップの表示範囲の調整
    map.attemptMove(QgsLayoutPoint(5, 15, QgsUnitTypes.LayoutMillimeters))
    map.attemptResize(QgsLayoutSize(200, 135, QgsUnitTypes.LayoutMillimeters))
    target_layer_extent = get_target_layer_extent(aggregated_layer)
    map.zoomToExtent(target_layer_extent)
    layout.addLayoutItem(map)

    # 凡例の追加
    legend = QgsLayoutItemLegend(layout)
    legend.setAutoUpdateModel(False)
    legend.setFrameEnabled(True)
    group = legend.model().rootGroup()
    group.clear()
    group.addLayer(QgsProject.instance().layerTreeRoot().findLayer(aggregated_layer.id()).layer())
    legend.setStyleFont(QgsLegendStyle.Subgroup,QFont('Meiryo UI', 10))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel,QFont('Meiryo UI', 10))
    layout.addItem(legend)
    legend.attemptMove(QgsLayoutPoint(167.2, 15, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(legend)

    # タイトルの追加
    map_label = QgsLayoutItemLabel(layout)
    map_label.setText(printlayout_name)
    map_label.setFont(QFont('Meiryo UI', 18, QFont.Bold))
    map_label.adjustSizeToText()
    layout.addLayoutItem(map_label)
    map_label.attemptMove(QgsLayoutPoint(79, 6, QgsUnitTypes.LayoutMillimeters))
    
    # 出典の追加
    source_label = QgsLayoutItemLabel(layout)
    source_label.setText("背景図の出典：○○○○")
    source_label.setFont(QFont('Meiryo UI', 10))
    source_label.adjustSizeToText()
    layout.addLayoutItem(source_label)
    source_label.attemptMove(QgsLayoutPoint(163, 150.6, QgsUnitTypes.LayoutMillimeters))
    
    # サブタイトルの追加
    map_summary_label = QgsLayoutItemLabel(layout)
    map_summary_label.setText("集計結果")
    map_summary_label.setFont(QFont('Meiryo UI', 14, QFont.Bold))
    map_summary_label.adjustSizeToText()
    map_summary_label.attemptMove(QgsLayoutPoint(5, 155, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map_summary_label)

    map_graph_label = QgsLayoutItemLabel(layout)
    map_graph_label.setText("結果グラフ")
    map_graph_label.setFont(QFont('Meiryo UI', 14, QFont.Bold))
    map_graph_label.adjustSizeToText()
    map_graph_label.attemptMove(QgsLayoutPoint(125, 155, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map_graph_label)

    # サマリーの追加
    map_summary = QgsLayoutItemLabel(layout)
    map_summary.setText(aggregated_summary)
    map_summary.setFont(QFont('Meiryo UI', 10))
    map_summary.setHAlign(Qt.AlignLeft)
    map_summary.adjustSizeToText()
    map_summary.attemptMove(QgsLayoutPoint(5, 163, QgsUnitTypes.LayoutMillimeters))
    map_summary.attemptResize(QgsLayoutSize(117, 128, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map_summary)

    # グラフの追加
    layoutItemPicture = QgsLayoutItemPicture(layout)
    layoutItemPicture.setPicturePath(graph_png_path)
    layoutItemPicture.attemptMove(QgsLayoutPoint(115, 164, QgsUnitTypes.LayoutMillimeters))
    layoutItemPicture.attemptResize(QgsLayoutSize(90, 95, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(layoutItemPicture)

    # レイアウトを開く
    iface.openLayoutDesigner(layout=layout)

def get_target_layer_extent(target_layer):
    """
    対象のレイヤーのextentをプロジェクトCRSに再投影してから返す
    Returns:
        QgsRectangle
    """
    target_layer_crs = target_layer.crs()
    project_crs = QgsProject.instance().crs()
    transform = QgsCoordinateTransform(target_layer_crs, project_crs, QgsProject.instance())
    extent = target_layer.extent()
    extent.grow(100) #少しだけズームアウト

    leftbottom = QgsPointXY(extent.xMinimum(), extent.yMinimum())
    righttop = QgsPointXY(extent.xMaximum(), extent.yMaximum())
    leftbottom_geom = QgsGeometry.fromPointXY(leftbottom)
    righttop_geom = QgsGeometry.fromPointXY(righttop)
    leftbottom_geom.transform(transform)
    righttop_geom.transform(transform)
    target_layer_extent = QgsRectangle(leftbottom_geom.asPoint(), righttop_geom.asPoint())
    return target_layer_extent