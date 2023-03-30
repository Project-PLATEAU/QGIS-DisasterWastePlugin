import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *

from .dockwidget_main import DockWidgetMain

PLUGIN_NAME = '災害廃棄物プラグイン'


class DisasterWastePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.win = self.iface.mainWindow()
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = PLUGIN_NAME
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.setObjectName(PLUGIN_NAME)
        self.dock_widget_main = None

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        self.actions.append(action)
        return action

    def initGui(self):
        # メニュー設定
        self.add_action(
            icon_path=None,
            text="災害廃棄物プラグイン",
            callback=self.show_dock_widget_main,
            parent=self.win)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(PLUGIN_NAME, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def show_dock_widget_main(self):
        if self.dock_widget_main is None:
            self.dock_widget_main = DockWidgetMain()
            # dockwidgetの×ボタンを無効にする
            self.dock_widget_main.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dock_widget_main.show()
