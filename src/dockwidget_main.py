import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.PyQt import uic
from qgis.utils import iface

from .aggregate_dialog import DialogMain


# uiファイルの定義と同じクラスを継承する
class DockWidgetMain(QDockWidget):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(os.path.join(os.path.dirname(
            __file__), 'dockwidget_main.ui'), self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self)
        self.init_ui()
        self.select_mode = False
        self.aggregate_dialog = None
        # 「選択をクリア」ボタンと「集計実行」ボタンを無効にする
        self.clearSelectionButton.setEnabled(False)
        self.aggregateRunButton.setEnabled(False)

        # コンボボックスに要素をセット
        self.set_temporary_strage_layer_fileds()
        self.set_aggregate_layer_fileds()

    def init_ui(self):
        # フィルタのセット
        self.buildingLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.temporaryStrageLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.aggregateLayerComboBox.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        # UIイベント設定
        self.temporaryStrageLayerComboBox.layerChanged.connect(self.set_temporary_strage_layer_fileds)
        self.aggregateLayerComboBox.layerChanged.connect(self.set_aggregate_layer_fileds)

        self.clearSelectionButton.clicked.connect(self.cancel_selection)
        self.selectAggregateRangeButton.clicked.connect(self.run_select_aggregate_range)
        self.aggregateRunButton.clicked.connect(self.run_aggregate)
        self.aggregateCancelButton.clicked.connect(self.close)

    def disconnect_signal(self):
        if self.current_layer_changed_signal:
            self.iface.currentLayerChanged.disconnect(self.current_layer_changed_signal)
            self.current_layer_changed_signal = False
        if self.selection_changed_signal:
            self.canvas.selectionChanged.disconnect(self.selection_changed_signal)
            self.selection_changed_signal = False

    def set_temporary_strage_layer_fileds(self):
        self.temporaryStrageNameField.setLayer(self.temporaryStrageLayerComboBox.currentLayer())
        self.temporaryStrageAreaField.setLayer(self.temporaryStrageLayerComboBox.currentLayer())
        self.temporaryStrageNameField.setFilters(QgsFieldProxyModel.String)
        self.temporaryStrageAreaField.setFilters(QgsFieldProxyModel.Numeric)

    def set_aggregate_layer_fileds(self):
        self.aggregateNameField.setLayer(self.aggregateLayerComboBox.currentLayer())
        self.aggregateNameField.setFilters(QgsFieldProxyModel.String)

    def run_select_aggregate_range(self):
        """集計ポリゴンを選択するメソッド"""
        if  self.select_mode is False:
            self.select_mode = True
            QMessageBox.information(None, "確認", "集計範囲を選択してください。", QMessageBox.Ok)
            aggregate_layer = self.aggregateLayerComboBox.currentLayer()
            self.set_polygon_table(aggregate_layer)

            # レイヤを表示させる
            layer = QgsProject.instance().layerTreeRoot().findLayer(aggregate_layer)
            layer.setItemVisibilityChecked(True)

            self.iface.setActiveLayer(aggregate_layer)
            self.iface.actionSelect().trigger()

            # 地物選択状態が変更されたら、テーブルを更新する
            self.selection_changed_signal = lambda: self.set_attributes_table(aggregate_layer)
            self.canvas.selectionChanged.connect(self.selection_changed_signal)

            # カレントレイヤが変更されたら、エラーメッセージを出す
            self.current_layer_changed_signal = lambda: self.current_layer_changed(aggregate_layer)
            self.iface.currentLayerChanged.connect(self.current_layer_changed_signal)

            # 「選択をクリア」と「集計実行」ボタンを有効にする
            self.clearSelectionButton.setEnabled(True)
            self.aggregateRunButton.setEnabled(True)
            # 「閉じる」のボタンを無効にする
            self.aggregateCancelButton.setEnabled(False)

            self.selectAggregateRangeButton.setText("選択モードをキャンセル")
        
        elif self.select_mode is True:
            self.select_mode = False
            self.cancel_selection()
            # シグナルを解除
            self.disconnect_signal()
            # 「選択をクリア」ボタンと「集計実行」ボタンを無効にする
            self.clearSelectionButton.setEnabled(False)
            self.aggregateRunButton.setEnabled(False)
            # 「閉じる」のボタンを有効にする
            self.aggregateCancelButton.setEnabled(True)

            self.selectAggregateRangeButton.setText("選択モードを開始")

    def cancel_selection(self):
        self.aggregateLayerComboBox.currentLayer().removeSelection()
        self.aggregateLayerTable.setRowCount(0)
        self.selectLabel.setText(f"選択ポリゴン数：0個")

    def set_polygon_table(self, aggregate_layer):
        """
        テーブルのヘッダーの設定を行う
        """
        aggregate_layer_fieldnames = aggregate_layer.fields().names()
        self.aggregateLayerTable.setColumnCount(len(aggregate_layer_fieldnames))
        self.aggregateLayerTable.setHorizontalHeaderLabels(aggregate_layer_fieldnames)

    def set_attributes_table(self, aggregate_layer):
        """
        テーブルに選択地物の属性をセットする
        """
        aggregate_layer_fieldnames = aggregate_layer.fields().names()
        self.aggregateLayerTable.setRowCount(0)
        select_features = aggregate_layer.selectedFeatures()

        for select_feature in select_features:
            row = self.aggregateLayerTable.rowCount()
            self.aggregateLayerTable.insertRow(row)

            for i, filed_name in enumerate(aggregate_layer_fieldnames):
                value = select_feature.attribute(filed_name)
                item = QTableWidgetItem()
                # intとfloatの場合は右揃え
                if isinstance(value, (int, float)):
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
                # NULLの場合は空白としたいため分岐
                if not value:
                    item.setData(Qt.EditRole, value)
                else:
                    item.setData(Qt.EditRole, str(value))
                self.aggregateLayerTable.setItem(row, i, item)
        
        self.selectLabel.setText(f"選択ポリゴン数：{len(select_features)}個")

    def current_layer_changed(self, aggregate_layer):
        # カレントレイヤを集計ポリゴンに戻す時はエラーメッセージを出さないようにする
        current_layer = iface.mapCanvas().currentLayer()
        if aggregate_layer == current_layer:
            return
        self.iface.setActiveLayer(aggregate_layer)
        QMessageBox.information(None, "確認", "集計範囲を選択中は、カレントレイヤを変更できません。\n変更したい場合は、「選択モードをキャンセル」を押してください。", QMessageBox.Ok)

    def run_aggregate(self):
        # 集計ダイアログに渡す値を取得する
        building_layer = self.buildingLayerComboBox.currentLayer()
        temporaryStrage_layer = self.temporaryStrageLayerComboBox.currentLayer()
        temporaryStrage_name_field = self.temporaryStrageNameField.currentField()
        temporaryStrage_area_field = self.temporaryStrageAreaField.currentField()
        aggregate_layer = self.aggregateLayerComboBox.currentLayer()
        aggregate_name_field = self.aggregateNameField.currentField()

        # 建物データが集計に必要なフィールドを持っているか検証
        building_layer_fieldnames = [field.name() for field in building_layer.fields()]
        is_bldlyr_valid = all(map(lambda x: x in building_layer_fieldnames,
                                  ["Bld_Str", "Cdst_Dmg", "Hdst_Dmg", "Prob_Burn", "Flam_out", "All_Out","Noflam_out", "T_Area"]))
        if not is_bldlyr_valid:
            QMessageBox.information(
                self, "確認", f"建物ポイントデータが不正です。\n選択したデータを確認してください。"
            )
            return

        # 集計ポリゴンの地物が選択されているか検証
        aggregate_selected_features = aggregate_layer.selectedFeatures()
        if len(aggregate_selected_features) == 0:
            QMessageBox.information(None, "ポリゴン選択", "集計範囲が選択されていません。\n集計範囲のポリゴンを選択してください。", QMessageBox.Ok)
            return
            
        # 集計ポリゴンの座標系の検証
        aggregate_layer_crs = aggregate_layer.crs()
        if not aggregate_layer_crs.isValid() or aggregate_layer_crs.isGeographic():
            QMessageBox.information(None, "座標参照系の確認", "集計ポリゴンの座標参照系が不正です。\n平面直角座標系に変換してください。", QMessageBox.Ok)
            return

        # 集計ポリゴンの選択地物に不正なジオメトリがないか検証
        for feature in aggregate_selected_features:
            geom = feature.geometry()
            validate_geom = geom.validateGeometry(QgsGeometry.ValidatorGeos)

            if validate_geom:
                # QMessageBox.Yesの場合はジオメトリ修復をした上で集計処理を実行する
                if QMessageBox.No == QMessageBox.question(
                    None,
                    "確認",
                    '集計ポリゴンに不正なジオメトリが存在します。\nジオメトリの修復を実行した上で集計を実行しますか？',
                    QMessageBox.Yes,
                    QMessageBox.No,
                ):
                    QMessageBox.information(None, "中止", "集計を中止しました。", QMessageBox.Ok)
                    return
                    
                continue

        # シグナルを解除
        self.disconnect_signal()

        # テーブルとラベルをクリアする
        self.aggregateLayerTable.setRowCount(0)
        self.selectLabel.setText(f"選択ポリゴン数：0個")

        # 「選択をクリア」ボタンと「集計実行」ボタンを無効にする
        self.clearSelectionButton.setEnabled(False)
        self.aggregateRunButton.setEnabled(False)
        
        # 「閉じる」のボタンを有効にする
        self.selectAggregateRangeButton.setEnabled(True)
        self.aggregateCancelButton.setEnabled(True)

        self.selectAggregateRangeButton.setText("選択モードを開始")


        self.select_mode = False
        
        # 2回連続で集計した場合、表示されているダイアログを閉じる
        if self.aggregate_dialog is not None:
            self.aggregate_dialog.hide()

        self.aggregate_dialog = DialogMain(
            building_layer,
            temporaryStrage_layer,
            temporaryStrage_name_field,
            temporaryStrage_area_field,
            aggregate_layer,
            aggregate_name_field,
        )
        self.aggregate_dialog.show()