import os
import tempfile

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.PyQt import uic
from qgis.utils import iface

from . import processes

# uiファイルの定義と同じクラスを継承する

class DialogMain(QDialog):
    def __init__(
            self,
            building_layer,
            tmp_storage_layer,
            tmp_storage_name_fieldname,
            tmp_storage_area_fieldname,
            aggregate_layer,
            aggregate_name_field,
    ):
        super().__init__()
        self.ui = uic.loadUi(os.path.join(os.path.dirname(
            __file__), 'aggregate_dialog.ui'), self)
        self.iface = iface
        self.building_layer = building_layer
        self.tmp_storage_layer = tmp_storage_layer
        self.tmp_storage_name_fieldname = tmp_storage_name_fieldname
        self.tmp_storage_area_fieldname = tmp_storage_area_fieldname
        self.aggregate_layer = aggregate_layer
        self.aggregate_name_field = aggregate_name_field
        self.init_ui()

        # 集計ポリゴンの選択地物で一時ファイルを作成
        selected_aggregate_feature = processes.aggregate.create_selected_aggregate_feature(
                                                                self.aggregate_layer,
                                                                self.aggregate_name_field
                                                                )

        # 集計処理実行
        self.aggregated_layer = processes.aggregate.run_aggregate(
                                                        self.aggregate_layer,
                                                        selected_aggregate_feature,
                                                        self.aggregate_name_field,
                                                        self.tmp_storage_layer,
                                                        self.tmp_storage_name_fieldname,
                                                        self.tmp_storage_area_fieldname,
                                                        self.building_layer
                                                        )

        # 集計レイヤで色塗り
        processes.aggregate.apply_symbology(self.aggregated_layer)

        # 集計レイヤにズーム
        layer_extent = processes.get_target_layer_extent(self.aggregated_layer)
        canvas = iface.mapCanvas()
        canvas.setExtent(layer_extent)

        # ダイアログにテーブルを追加
        self.set_attributes_table(self.aggregated_layer)
        self.aggregatedLayerTable.itemClicked.connect(lambda: self.zoom_selected_feature(self.aggregated_layer))

        # ダイアログに集計サマリーを追加
        self.aggregated_summary_layer, self.aggregated_summary_text = self.create_summary(self.aggregated_layer)

        # ダイアログにグラフを追加
        self.graph_png_path = self.plot_graph(self.aggregated_summary_layer)

    def init_ui(self):
        # connect signals
        self.closeWindowButton.clicked.connect(lambda: self.hide())

        self.summaryCsvExportButton.clicked.connect(lambda: processes.export_csv(self.aggregated_summary_layer))
        self.aggregatedCsvExportButton.clicked.connect(lambda: processes.export_csv(self.aggregated_layer))

        self.printlayoutExportButton.clicked.connect(
            lambda: processes.create_printlayout(self.aggregated_layer, self.aggregated_summary_text, self.graph_png_path))

    def set_attributes_table(self, aggregated_layer):
        """
        テーブルに属性をセットする

        Args:
            aggregated_layer(QgsVectorLayer): 集計レイヤ

        Returns:
            None
        """
        # ヘッダーの設定
        aggregate_layer_fieldnames = aggregated_layer.fields().names()
        self.aggregatedLayerTable.setColumnCount(len(aggregate_layer_fieldnames))
        self.aggregatedLayerTable.setHorizontalHeaderLabels(aggregate_layer_fieldnames)

        # 属性のセット
        aggregated_layer_fieldnames = aggregated_layer.fields().names()
        self.aggregatedLayerTable.setRowCount(0)
        aggregated_layer_features = aggregated_layer.getFeatures()

        for feature in aggregated_layer_features:
            row = self.aggregatedLayerTable.rowCount()
            self.aggregatedLayerTable.insertRow(row)

            for i, filed_name in enumerate(aggregated_layer_fieldnames):
                value = feature.attribute(filed_name)
                item = QTableWidgetItem()
                # intとfloatの場合は右揃え
                if isinstance(value, (int, float)):
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
                # NULLの場合は空白としたいため分岐
                if not value:
                    item.setData(Qt.EditRole, value)
                else:
                    item.setData(Qt.EditRole, str(value))
                self.aggregatedLayerTable.setItem(row, i, item)

    def zoom_selected_feature(self, aggregated_layer):
        """
        選択した行の地物を選択状態にする

        Args:
            aggregated_layer(QgsVectorLayer): 集計レイヤ

        Returns:
            None
        """
        # 選択した行の地物を選択状態にする
        selected_indexes = self.aggregatedLayerTable.selectedIndexes()
        selected_name = self.aggregatedLayerTable.item(selected_indexes[0].row(), 1).text()
        aggregated_layer.selectByExpression(f"\"{self.aggregate_name_field}\"='{selected_name}'")
        current_scale = self.iface.mapCanvas().scale()
        self.iface.mapCanvas().zoomToSelected()
        self.iface.mapCanvas().zoomScale(current_scale)

    def create_summary(self, aggregated_layer):
        """
        集計結果レイヤから集計サマリーを作成する

        Args:
            aggregated_layer(QgsVectorLayer): 集計レイヤ

        Returns:
            refactor_aggregated_summary(QgsVectorLayer): 集計レイヤをひとつのポリゴンとして再集計したレイヤ
            aggregated_summary(str): 集計サマリーの文字列
        """
        aggregated_summary_layer = processes.processing.aggregate(aggregated_layer, [
            {'aggregate': 'concatenate', 'delimiter': '、', 'input': f'"{self.aggregate_name_field}"', 'length': 0,
             'name': self.aggregate_name_field, 'precision': 0, 'type': 10},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"面積"', 'length': 0, 'name': '範囲内面積', 'precision': 1,
             'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物棟数（木造）"', 'length': 0, 'name': '建物棟数（木造）',
             'precision': 1, 'type': 4},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物棟数（非木造）"', 'length': 0, 'name': '建物棟数（非木造）',
             'precision': 1, 'type': 4},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物棟数（合計）"', 'length': 0, 'name': '建物棟数（合計）',
             'precision': 1, 'type': 4},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（木造：全壊）"', 'length': 0, 'name': '建物被害想定（木造：全壊）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（木造：半壊）"', 'length': 0, 'name': '建物被害想定（木造：半壊）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（木造：焼失）"', 'length': 0, 'name': '建物被害想定（木造：焼失）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（非木造：全壊）"', 'length': 0, 'name': '建物被害想定（非木造：全壊）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（非木造：半壊）"', 'length': 0, 'name': '建物被害想定（非木造：半壊）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（非木造：焼失）"', 'length': 0, 'name': '建物被害想定（非木造：焼失）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（合計：全壊）"', 'length': 0, 'name': '建物被害想定（合計：全壊）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（合計：半壊）"', 'length': 0, 'name': '建物被害想定（合計：半壊）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"建物被害想定（合計：焼失）"', 'length': 0, 'name': '建物被害想定（合計：焼失）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"災害廃棄物の発生量（可燃系）"', 'length': 0, 'name': '災害廃棄物の発生量（可燃系）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"災害廃棄物の発生量（不燃系）"', 'length': 0, 'name': '災害廃棄物の発生量（不燃系）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"災害廃棄物の発生量（合計）"', 'length': 0, 'name': '災害廃棄物の発生量（合計）',
             'precision': 1, 'type': 6},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"仮置場必要面積"', 'length': 0, 'name': '仮置場必要面積', 'precision': 1,
             'type': 6},
            {'aggregate': 'concatenate', 'delimiter': '、', 'input': ' coalesce("仮置場名称",\'none\')', 'length': 0,
             'name': '仮置場名称', 'precision': 0, 'type': 10},
            {'aggregate': 'sum', 'delimiter': ',', 'input': '"仮置場概略有効面積"', 'length': 0, 'name': '仮置場概略有効面積',
             'precision': 0, 'type': 6}],"NULL"
             )

        for feature in aggregated_summary_layer.getFeatures():
            number_of_buildings_total = "{:,}".format(feature["建物棟数（合計）"])
            number_of_buildings_wooden = "{:,}".format(feature["建物棟数（木造）"])
            number_of_buildings_non_wooden = "{:,}".format(feature["建物棟数（非木造）"])
            building_damage_total_cdst = "{:,}".format(round(feature["建物被害想定（合計：全壊）"], 1))
            building_damage_wooden_cdst = "{:,}".format(round(feature["建物被害想定（木造：全壊）"], 1))
            building_damage_non_wooden_cdst = "{:,}".format(round(feature["建物被害想定（非木造：全壊）"], 1))
            building_damage_total_hdst = "{:,}".format(round(feature["建物被害想定（合計：半壊）"], 1))
            building_damage_wooden_hdst = "{:,}".format(round(feature["建物被害想定（木造：半壊）"], 1))
            building_damage_non_wooden_hdst = "{:,}".format(round(feature["建物被害想定（非木造：半壊）"], 1))
            building_damage_total_prob = "{:,}".format(round(feature["建物被害想定（合計：焼失）"], 1))
            building_damage_wooden_prob = "{:,}".format(round(feature["建物被害想定（木造：焼失）"], 1))
            building_damage_non_wooden_prob = "{:,}".format(round(feature["建物被害想定（非木造：焼失）"], 1))
            disaster_wastes_total = "{:,}".format(round(feature["災害廃棄物の発生量（合計）"], 1))
            disaster_wastes_flam = "{:,}".format(round(feature["災害廃棄物の発生量（可燃系）"], 1))
            disaster_wastes_no_flam = "{:,}".format(round(feature["災害廃棄物の発生量（不燃系）"], 1))
            range_area = "{:,}".format(round(feature["範囲内面積"], 1))
            disaster_waste_required_area = "{:,}".format(round(feature["仮置場必要面積"], 1))
            tmp_storage_effective_area = "{:,}".format(round(feature["仮置場概略有効面積"], 1))

            # 仮置場名称の文字列を置換する
            field_idx = aggregated_summary_layer.fields().indexOf('仮置場名称')
            aggregated_summary_layer.startEditing()
            tmp_storage_name = feature["仮置場名称"].replace('none、', '').replace('、none', '')
            if tmp_storage_name == "none":
                tmp_storage_name = ""
            aggregated_summary_layer.changeAttributeValue(1, field_idx, tmp_storage_name)
            aggregated_summary_layer.commitChanges

            # 使用率の計算
            if feature["仮置場必要面積"] == 0 or feature["仮置場概略有効面積"] == 0:
                usage_percentage = " - "
            else:
                usage_percentage = round(feature["仮置場必要面積"] / feature["仮置場概略有効面積"] * 100)
            aggregate_polygon_name = feature[self.aggregate_name_field]

        aggregated_summary_text = f"""＜建物棟数＞
合計：{number_of_buildings_total}棟（木造：{number_of_buildings_wooden}棟、非木造：{number_of_buildings_non_wooden}棟）

＜範囲内面積＞
{range_area}㎡

＜建物被害想定棟数＞
全壊：{building_damage_total_cdst}棟（木造：{building_damage_wooden_cdst}棟、非木造：{building_damage_non_wooden_cdst}棟）
半壊：{building_damage_total_hdst}棟（木造：{building_damage_wooden_hdst}棟、非木造：{building_damage_non_wooden_hdst}棟）
焼失：{building_damage_total_prob}棟（木棟：{building_damage_wooden_prob}棟、非木造：{building_damage_non_wooden_prob}棟）

＜災害廃棄物発生量＞
合計： {disaster_wastes_total}t（可燃系：{disaster_wastes_flam}t、不燃系：{disaster_wastes_no_flam}t）

＜仮置場必要面積＞
{disaster_waste_required_area}㎡

＜仮置場情報＞
名称：{tmp_storage_name}
仮置場概略有効面積：{tmp_storage_effective_area}㎡
使用率：{usage_percentage}％

＜集計ポリゴン名称＞
{aggregate_polygon_name}"""

        self.aggregatedSummaryLabel.setText(aggregated_summary_text)
        self.aggregatedSummaryLabel.setFont(QFont('Meiryo UI', 10))

        return aggregated_summary_layer, aggregated_summary_text

    def plot_graph(self, aggregated_summary_layer):
        """
        集計レイヤの値からグラフを作成する

        Args:
            aggregated_layer(QgsVectorLayer): 集計レイヤ

        Returns:
            None
        """
        height = []
        for feature in aggregated_summary_layer.getFeatures():
            height = [round(feature["仮置場概略有効面積"], 1), round(feature["仮置場必要面積"], 1)]
        label = ["仮置場概略\n有効面積", "仮置場\n必要面積"]

        # フォントの設定
        plt.rcParams['font.family'] = 'Meiryo'

        # 集計結果が0の場合はグラフをplotしない
        if sum(height) == 0:
            return

        fig, ax = plt.subplots(figsize=(4.0, 3.8))
        graph = ax.bar(label, height, width=0.5)
        
        # フォントサイズの調整
        plt.tick_params(axis='x', which='major', labelsize=12)
        plt.tick_params(axis='y', which='major', labelsize=11)

        # 枠の色の調整
        ax.spines["right"].set_color("#a9a9a9")
        ax.spines["bottom"].set_color("#a9a9a9")
        ax.spines["left"].set_color("#a9a9a9")
        ax.spines["top"].set_color("#a9a9a9")

        # X軸・Y軸の表示範囲を調整e
        ax.set_xlim(-0.4, 1.4)
        ax.set_ylim(0, max(height) * 1.2)
        # 余白の調整
        fig.subplots_adjust(left=0.25, bottom=0.2)
        # Y軸に三桁カンマの設定
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
        # 棒グラフのカラーの設定
        graph[0].set_color('#87ceeb')
        graph[1].set_color('#f4a460')

        # 棒グラフの上部に数値を表示する
        for rect in graph:
            height = rect.get_height()
            plt.annotate('{:,}'.format(height) + "㎡",
                         xy=(rect.get_x() + rect.get_width() / 2, height),
                         xytext=(0, 3),
                         size = 11,
                         textcoords="offset points",
                         ha='center', va='bottom')

        canvas = FigureCanvas(fig)
        canvas.setFixedHeight(400)
        canvas.setFixedWidth(380)
        self.ui.graphAreaFrame.layout().addWidget(canvas)

        # 一時ディレクトリにグラフをpngで保存
        temp_dir = tempfile.mkdtemp()
        graph_png_path = os.path.join(temp_dir, "graph.png")
        fig.savefig(graph_png_path)

        return graph_png_path
