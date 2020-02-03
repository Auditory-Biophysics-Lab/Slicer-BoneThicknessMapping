import inspect

import ctk
import slicer
import numpy
import time
import qt
import vtk
import colorsys
from slicer.ScriptedLoadableModule import *


# Interface tools
class InterfaceTools:
    def __init__(self):
        pass

    @staticmethod
    def build_vertical_space(height=18):
        s = qt.QWidget()
        s.setFixedSize(10, height)
        return s

    @staticmethod
    def build_dropdown(title, disabled=False):
        d = ctk.ctkCollapsibleButton()
        d.text = title
        d.enabled = not disabled
        d.collapsed = disabled
        return d

    @staticmethod
    def build_frame():
        g = qt.QFrame()
        g.setFrameStyle(3)
        return g

    @staticmethod
    def build_volume_selector(on_click=None):
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        s.noneEnabled = True
        s.addEnabled = False
        s.renameEnabled = True
        s.setMRMLScene(slicer.mrmlScene)
        if on_click is not None: s.connect("currentNodeChanged(bool)", on_click)
        return s

    @staticmethod
    def build_model_selector(on_click=None):
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLModelNode"]
        s.addEnabled = False
        s.renameEnabled = s.noneEnabled = False  # True
        s.setMRMLScene(slicer.mrmlScene)
        if on_click is not None: s.connect("currentNodeChanged(bool)", on_click)
        return s

    @staticmethod
    def build_spin_box(minimum, maximum, click=None, decimals=0, step=1.0, initial=0.0, width=None):
        box = qt.QDoubleSpinBox()
        box.setMinimum(minimum)
        box.setMaximum(maximum)
        box.setSingleStep(step)
        box.setDecimals(decimals)
        box.setValue(initial)
        if width is not None: box.setFixedWidth(width)
        if click is not None: box.connect('valueChanged(double)', click)
        return box

    @staticmethod
    def build_radio_button(title, on_click, checked=False, tooltip=None, width=None):
        b = qt.QRadioButton(title)
        b.connect('clicked(bool)', on_click)
        b.setChecked(checked)
        if tooltip is not None: b.setToolTip(tooltip)
        if width is not None: b.setFixedWidth(width)
        return b

    @staticmethod
    def build_label(text, width=None):
        b = qt.QLabel(text)
        if width is not None: b.setFixedWidth(width)
        return b

    @staticmethod
    def build_icon_button(icon_path, on_click, width=50, tooltip=None):
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + icon_path
        icon = qt.QPixmap(path).scaled(qt.QSize(16, 16), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
        b = qt.QToolButton()
        b.setIcon(qt.QIcon(icon))
        b.setFixedSize(width, 24)
        if tooltip is not None: b.setToolTip(tooltip)
        b.connect('clicked(bool)', on_click)
        return b

    @staticmethod
    def build_min_max(initial, decimals=2, step=0.1, lb=0.0, hb=1000.0, units='mm', min_text='MIN: ', max_text='MAX: '):
        def set_min(value): initial[0] = value
        def set_max(value): initial[1] = value
        box = qt.QHBoxLayout()
        box.addStretch()
        box.addWidget(InterfaceTools.build_label(min_text, 40))
        lowerSb = InterfaceTools.build_spin_box(lb, hb, decimals=decimals, step=step, initial=initial[0], click=set_min, width=80)
        box.addWidget(lowerSb)
        box.addWidget(InterfaceTools.build_label(units, 50))
        box.addWidget(InterfaceTools.build_label(max_text, 40))
        higherSb = InterfaceTools.build_spin_box(lb, hb, decimals=decimals, step=step, initial=initial[1], click=set_max, width=80)
        box.addWidget(higherSb)
        box.addWidget(InterfaceTools.build_label(units, 30))
        def set_boxes(value=None, enabled=None):
            if value is not None:
                set_min(value[0])
                lowerSb.setValue(value[0])
                set_max(value[0])
                higherSb.setValue(value[1])
            if enabled is not None:
                lowerSb.enabled = enabled
                higherSb.enabled = enabled
        return box, set_boxes


class BoneThicknessMappingType:
    THICKNESS = 'Thickness to dura'
    AIR_CELL = 'Distance to first air cell'


class BoneThicknessMappingState:
    WAITING = 1
    READY = 2
    EXECUTING = 3
    FINISHED = 4


class BoneThicknessMappingQuality:
    VERY_LOW = 'VERY LOW (ray every 4 dimensional units)'
    LOW = 'LOW (ray every 2 dimensional units)'
    MEDIUM = 'MEDIUM (ray every 1 dimensional unit)'
    HIGH = 'HIGH (ray every 0.5 dimensional units)'
    VERY_HIGH = 'VERY HIGH (ray every 0.25 dimensional units)'


class RayDirection:
    R = 'R'
    L = 'L'
    A = 'A'
    P = 'P'
    S = 'S'
    I = 'I'


class HitPoint:
    pid = None
    point = None
    normal = [0.0, 0.0, 0.0]

    def __init__(self, pid, point):
        self.pid = pid
        self.point = point


class BoneThicknessMapping(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Bone Thickness Mapping"
        self.parent.categories = ["Shape Analysis"]
        self.parent.dependencies = []
        self.parent.contributors = ["Evan Simpson (Western University)"]
        self.parent.helpText = "The following module will segment and threshold a volume to isolate bone material, cast rays in one direction to calculate the thickness of segmented bone, finally a gradient visualization will be rendered on the 3D segment model." \
                               "\nVersion 1.0-2020.02.03" \
                               + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This module was originally developed by Evan Simpson at The University of Western Ontario in the HML/SKA Auditory Biophysics Lab."


class BoneThicknessMappingWidget(ScriptedLoadableModuleWidget):
    # Data members --------------
    state = BoneThicknessMappingState.WAITING
    status, progress = 'N/A', 0
    thicknessScalarArray, airCellScalarArray = None, None
    thicknessColourNode, airCellColourNode = None, None
    modelPolyData = None
    topLayerPolyData = None
    hitPointList = None
    modelNode = None

    # Configuration preferences
    CONFIG_precision = 1.0
    CONFIG_rayDirection = 'L'
    CONFIG_segmentThresholdRange = [600, 3071]
    CONFIG_regionOfInterest = [-100, 100]
    CONFIG_minMaxAirCell = [0.0, 4.0]
    CONFIG_minMaxSkullThickness = [0.0, 8.7]

    # UI members (in order of appearance) --------------
    infoLabel = None
    volumeSelector = None
    configuration_tools = None
    statusLabel = None
    executeButton = None
    progressBar = None
    finishButton = None
    resultSection = None
    displayThicknessSelector = None
    displayFirstAirCellSelector = None
    displayScalarBarCheckbox = None

    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addLayout(self.build_input_tools())
        self.layout.addLayout(self.build_execution_tools())
        self.layout.addLayout(self.build_result_tools())
        self.layout.addStretch()
        BoneThicknessMappingLogic.reset_view(RayDirection.L)
        self.update_all()

    # interface build ------------------------------------------------------------------------------
    def build_input_tools(self):
        layout = qt.QVBoxLayout()

        self.volumeSelector = InterfaceTools.build_volume_selector(on_click=self.update_all)
        box = qt.QHBoxLayout()
        box.addWidget(self.volumeSelector)
        box.addWidget(InterfaceTools.build_icon_button('/Resources/Icons/fit.png', on_click=lambda: BoneThicknessMappingLogic.reset_view(self.CONFIG_rayDirection), tooltip="Reset 3D view."))
        form = qt.QFormLayout()
        form.addRow("Input Volume: ", box)
        self.infoLabel = qt.QLabel()
        form.addWidget(self.infoLabel)

        title = qt.QHBoxLayout()
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Icons/logo.png"
        icon = qt.QPixmap(path).scaled(qt.QSize(240, 400), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
        logo = qt.QLabel()
        logo.setPixmap(icon)
        title.addWidget(logo)
        title.addWidget(qt.QLabel('\n\n\n\nSelect an input volume to auto-segment, render, and calculate thickness.'))

        layout.addLayout(title)
        layout.addLayout(form)
        layout.setMargin(10)
        return layout

    def build_configuration_tools(self):
        self.configuration_tools = InterfaceTools.build_dropdown("Configuration")
        layout = qt.QFormLayout(self.configuration_tools)

        # threshold
        group_box = qt.QGroupBox('Segment Thresholding')
        group_layout = qt.QFormLayout(group_box)
        threshBox, setThresh = InterfaceTools.build_min_max(self.CONFIG_segmentThresholdRange, step=5.0, decimals=2, lb=-3020, hb=3071, units='')
        group_layout.addRow("Casting bounds (along cast direction):", threshBox)
        layout.addRow(group_box)

        # ray direction
        def set_direction(d):
            self.CONFIG_rayDirection = d
            # SkullThicknessMappingLogic.reset_view(d)
        box = qt.QVBoxLayout()
        row1 = qt.QHBoxLayout()
        row1.addStretch()
        row1.addWidget(InterfaceTools.build_radio_button(RayDirection.R, lambda: set_direction(RayDirection.R), width=100))
        row1.addWidget(InterfaceTools.build_radio_button(RayDirection.A, lambda: set_direction(RayDirection.A), width=100))
        row1.addWidget(InterfaceTools.build_radio_button(RayDirection.S, lambda: set_direction(RayDirection.S), width=100))
        row2 = qt.QHBoxLayout()
        row2.addStretch()
        row2.addWidget(InterfaceTools.build_radio_button(RayDirection.L, lambda: set_direction(RayDirection.L), width=100, checked=True))
        row2.addWidget(InterfaceTools.build_radio_button(RayDirection.P, lambda: set_direction(RayDirection.P), width=100))
        row2.addWidget(InterfaceTools.build_radio_button(RayDirection.I, lambda: set_direction(RayDirection.I), width=100))
        box.addLayout(row1)
        box.addLayout(row2)

        # region of interest
        roiBox, setRoi = InterfaceTools.build_min_max(self.CONFIG_regionOfInterest, step=1.0, decimals=0, lb=-1000, hb=1000, units='units')

        # add ray-casting box
        group_box = qt.QGroupBox('Ray-casting')
        group_layout = qt.QFormLayout(group_box)
        group_layout.addRow("Cast direction: ", box)
        group_layout.addRow("Casting bounds (along cast direction):", roiBox)
        layout.addRow(InterfaceTools.build_vertical_space())
        layout.addRow(group_box)

        # degrees of interest
        # TODO

        # min/max
        skullBox, setSkullBoxes = InterfaceTools.build_min_max(self.CONFIG_minMaxSkullThickness)
        airCellBox, setAirBoxes = InterfaceTools.build_min_max(self.CONFIG_minMaxAirCell)
        comboBox = qt.QComboBox()
        comboBox.addItems(['Manual', 'BCI 601', 'BCI 602'])
        comboBox.setFixedWidth(350)
        def current_index_changed(string):
            if string == 'BCI 601':
                setSkullBoxes([0.0, 8.7], enabled=False)
                setAirBoxes([0.0, 4.0], enabled=False)
            elif string == 'BCI 602':
                setSkullBoxes([0.0, 4.5], enabled=False)
                setAirBoxes([0.0, 4.0], enabled=False)
            elif string == 'Manual':
                setSkullBoxes(enabled=True)
                setAirBoxes(enabled=True)
        comboBox.connect("currentIndexChanged(QString)", current_index_changed)
        box = qt.QHBoxLayout()
        box.addStretch()
        box.addWidget(comboBox)

        # add ray-casting box
        group_box = qt.QGroupBox('Depth mapping')
        g_layout = qt.QFormLayout(group_box)
        g_layout.addRow('Depth preset: ', box)
        g_layout.addRow("Thickness depth: ", skullBox)
        g_layout.addRow("Air cell depth: ", airCellBox)
        layout.addRow(InterfaceTools.build_vertical_space())
        layout.addRow(group_box)

        # quality
        comboBox = qt.QComboBox()
        comboBox.addItems([BoneThicknessMappingQuality.VERY_LOW, BoneThicknessMappingQuality.LOW, BoneThicknessMappingQuality.MEDIUM, BoneThicknessMappingQuality.HIGH, BoneThicknessMappingQuality.VERY_HIGH])
        comboBox.setCurrentIndex(2)
        comboBox.setFixedWidth(350)
        def current_index_changed(string):
            if string == BoneThicknessMappingQuality.VERY_LOW: self.CONFIG_precision = 4.0
            elif string == BoneThicknessMappingQuality.LOW: self.CONFIG_precision = 2.0
            elif string == BoneThicknessMappingQuality.MEDIUM: self.CONFIG_precision = 1.0
            elif string == BoneThicknessMappingQuality.HIGH: self.CONFIG_precision = 0.50
            elif string == BoneThicknessMappingQuality.VERY_HIGH: self.CONFIG_precision = 0.25
        comboBox.connect("currentIndexChanged(QString)", current_index_changed)
        box = qt.QHBoxLayout()
        box.addStretch()
        box.addWidget(comboBox)

        # add ray-casting box
        group_box = qt.QGroupBox('Rendering')
        g_layout = qt.QFormLayout(group_box)
        g_layout.addRow("Render quality: ", box)
        layout.addRow(InterfaceTools.build_vertical_space())
        layout.addRow(group_box)

        layout.addRow(InterfaceTools.build_vertical_space())
        layout.setMargin(10)
        return self.configuration_tools

    def build_execution_tools(self):
        self.executeButton = qt.QPushButton('Execute')
        self.executeButton.setFixedHeight(36)
        self.executeButton.connect('clicked(bool)', self.click_execute)
        self.statusLabel = qt.QLabel('Status: ')
        self.statusLabel.enabled = False
        self.progressBar = qt.QProgressBar()
        self.progressBar.setFixedHeight(36)
        self.progressBar.minimum = 0
        self.progressBar.maximum = 100
        self.progressBar.value = 0
        self.progressBar.visible = False
        self.finishButton = qt.QPushButton('Finish')
        self.finishButton.visible = False
        self.finishButton.connect('clicked(bool)', self.click_finish)
        self.finishButton.setFixedHeight(36)
        box = qt.QHBoxLayout()
        box.addWidget(self.progressBar)
        box.addWidget(self.finishButton)

        layout = qt.QVBoxLayout()
        layout.addWidget(self.build_configuration_tools())
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.executeButton)
        layout.addLayout(box)
        layout.setMargin(10)
        return layout

    def build_result_tools(self):
        self.resultSection = InterfaceTools.build_frame()

        self.displayThicknessSelector = InterfaceTools.build_radio_button(BoneThicknessMappingType.THICKNESS, self.click_result_radio, checked=True)
        self.displayFirstAirCellSelector = InterfaceTools.build_radio_button(BoneThicknessMappingType.AIR_CELL, self.click_result_radio)

        box = qt.QVBoxLayout()
        box.addWidget(self.displayThicknessSelector)
        box.addWidget(self.displayFirstAirCellSelector)

        self.displayScalarBarCheckbox = qt.QCheckBox()
        self.displayScalarBarCheckbox.checked = True
        self.displayScalarBarCheckbox.connect("stateChanged(int)", self.click_toggle_scalar_bar)

        form = qt.QFormLayout(self.resultSection)
        # form.addRow('Results', qt.QWidget())
        form.addRow("Map Display: ", box)
        # form.addRow(qt.QLayout())
        form.addRow("Display Scalar Bar: ", self.displayScalarBarCheckbox)
        form.setContentsMargins(10, 8, 10, 14)

        layout = qt.QVBoxLayout()
        layout.addWidget(self.resultSection)
        layout.setContentsMargins(12, 0, 12, 10)
        return layout

    # interface update ------------------------------------------------------------------------------
    def update_all(self):
        self.update_input_tools()
        self.update_execution_tools()
        self.update_results()

    def update_input_tools(self):
        if self.volumeSelector.currentNode() is None:
            self.volumeSelector.enabled = True
            self.infoLabel.text = 'Dimensions: '
            self.infoLabel.enabled = False
            self.state = BoneThicknessMappingState.WAITING
        elif self.state is BoneThicknessMappingState.WAITING and self.volumeSelector.currentNode() is not None:
            self.volumeSelector.enabled = True
            self.infoLabel.enabled = True
            self.infoLabel.text = 'Dimensions: ' + str(self.volumeSelector.currentNode().GetImageData().GetDimensions())
            self.state = BoneThicknessMappingState.READY
            # self.modelPolyData = SkullThicknessMappingLogic.process_segmentation(image=self.volumeSelector.currentNode(), update_status=self.update_status)
        elif self.state is BoneThicknessMappingState.EXECUTING or self.state is BoneThicknessMappingState.FINISHED:
            self.volumeSelector.enabled = False

    def update_execution_tools(self):
        if self.state is BoneThicknessMappingState.WAITING:
            self.configuration_tools.enabled = True
            self.configuration_tools.collapsed = True
            self.executeButton.visible = True
            self.executeButton.enabled = False
            self.progressBar.visible = False
            self.progressBar.value = 0
            self.statusLabel.enabled = False
            self.statusLabel.text = 'Status: WAITING'
            self.finishButton.visible = False
        elif self.state is BoneThicknessMappingState.READY:
            self.configuration_tools.enabled = True
            self.executeButton.visible = True
            self.executeButton.enabled = True
            self.progressBar.visible = False
            self.progressBar.value = 0
            self.statusLabel.enabled = True
            self.statusLabel.text = 'Status: READY'
            self.finishButton.visible = False
        elif self.state is BoneThicknessMappingState.EXECUTING:
            self.configuration_tools.enabled = False
            self.configuration_tools.collapsed = True
            self.executeButton.visible = False
            self.executeButton.enabled = False
            self.progressBar.visible = True
            self.progressBar.value = self.progress
            self.statusLabel.enabled = True
            self.statusLabel.text = 'Status: ' + str(self.status)
            self.finishButton.visible = False
        elif self.state is BoneThicknessMappingState.FINISHED:
            self.configuration_tools.enabled = False
            self.configuration_tools.collapsed = True
            self.progressBar.value = 100
            self.executeButton.visible = False
            self.finishButton.visible = True

    def update_results(self):
        if self.thicknessScalarArray is not None and self.airCellScalarArray is not None:
            self.resultSection.enabled = True
        else: self.resultSection.enabled = False

    def update_status(self, text=None, progress=None):
        if text is not None:
            print(text)
            self.status = str(text)
        if progress is not None:
            self.progress = progress
        self.update_all()
        slicer.app.processEvents()

    # interface click events ----------------------------------------------------------------------
    def click_execute(self):
        # TODO add try and catch
        if self.state is not BoneThicknessMappingState.READY: return
        self.state = BoneThicknessMappingState.EXECUTING
        self.update_status(text='Initializing execution..', progress=0)
        BoneThicknessMappingLogic.reset_view(self.CONFIG_rayDirection)
        BoneThicknessMappingLogic.set_scalar_colour_bar_state(0)
        self.modelPolyData = BoneThicknessMappingLogic.process_segmentation(
            threshold_range=self.CONFIG_segmentThresholdRange,
            image=self.volumeSelector.currentNode(),
            update_status=self.update_status
        )
        self.topLayerPolyData, self.hitPointList = BoneThicknessMappingLogic.rainfall_quad_cast(
            poly_data=self.modelPolyData,
            dimensions=self.volumeSelector.currentNode().GetImageData().GetDimensions(),
            ray_direction=self.CONFIG_rayDirection,
            precision=self.CONFIG_precision,
            region_of_interest=self.CONFIG_regionOfInterest,
            update_status=self.update_status
        )
        self.modelNode = BoneThicknessMappingLogic.build_model(
            poly_data=self.topLayerPolyData,
            update_status=self.update_status
        )
        self.thicknessScalarArray, self.airCellScalarArray = BoneThicknessMappingLogic.ray_cast_color_thickness(
            poly_data=self.modelPolyData,
            hit_point_list=self.hitPointList,
            ray_direction=self.CONFIG_rayDirection,
            dimensions=self.volumeSelector.currentNode().GetImageData().GetDimensions(),
            update_status=self.update_status
        )
        self.thicknessColourNode, self.airCellColourNode = BoneThicknessMappingLogic.build_color_tables(
            minmax_thickness=self.CONFIG_minMaxSkullThickness,
            minmax_air_cell=self.CONFIG_minMaxAirCell
        )
        self.click_result_radio()
        self.state = BoneThicknessMappingState.FINISHED
        self.update_status(progress=100)

    def click_finish(self):
        self.state = BoneThicknessMappingState.WAITING
        self.update_all()

    def click_result_radio(self):
        if self.thicknessScalarArray is None or self.airCellScalarArray is None: return  # TODO add error message
        scalar, scalarName, colourNodeId = None, None, None
        if self.displayThicknessSelector.isChecked():
            scalar = self.thicknessScalarArray
            scalarName = BoneThicknessMappingType.THICKNESS
            colourNodeId = self.thicknessColourNode.GetID()
        elif self.displayFirstAirCellSelector.isChecked():
            scalar = self.airCellScalarArray
            scalarName = BoneThicknessMappingType.AIR_CELL
            colourNodeId = self.airCellColourNode.GetID()
        # update poly data
        self.topLayerPolyData.GetPointData().SetScalars(scalar)
        self.topLayerPolyData.Modified()
        # update display node
        displayNode = self.modelNode.GetDisplayNode()
        displayNode.SetActiveScalarName(scalarName)
        displayNode.SetAndObserveColorNodeID(colourNodeId)
        displayNode.ScalarVisibilityOn()
        displayNode.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
        # update scalar bar
        BoneThicknessMappingLogic.set_scalar_colour_bar_state(1, colourNodeId)
        # reset view
        BoneThicknessMappingLogic.reset_view(self.CONFIG_rayDirection)

    def click_toggle_scalar_bar(self, state):
        if state is 0: BoneThicknessMappingLogic.set_scalar_colour_bar_state(0)
        elif state is 2:
            if self.displayThicknessSelector.isChecked(): BoneThicknessMappingLogic.set_scalar_colour_bar_state(1, self.thicknessColourNode)
            elif self.displayFirstAirCellSelector.isChecked(): BoneThicknessMappingLogic.set_scalar_colour_bar_state(1, self.airCellColourNode)


class BoneThicknessMappingLogic(ScriptedLoadableModuleLogic):
    @staticmethod
    def sample_folder():
        return slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Sample/'

    @staticmethod
    def reset_view(cast_direction):
        m = slicer.app.layoutManager()
        m.setLayout(16)
        w = m.threeDWidget(0)
        axis = None
        if cast_direction is RayDirection.R: axis = ctk.ctkAxesWidget.Right
        elif cast_direction is RayDirection.L: axis = ctk.ctkAxesWidget.Left
        elif cast_direction is RayDirection.A: axis = ctk.ctkAxesWidget.Anterior
        elif cast_direction is RayDirection.P: axis = ctk.ctkAxesWidget.Posterior
        elif cast_direction is RayDirection.S: axis = ctk.ctkAxesWidget.Superior
        elif cast_direction is RayDirection.I: axis = ctk.ctkAxesWidget.Inferior
        w.threeDView().lookFromViewAxis(axis)
        # Reset zoom
        w.threeDView().renderWindow().GetRenderers().GetFirstRenderer().ResetCamera()
        c = w.threeDController()
        for i in range(12): c.zoomIn()

    @staticmethod
    def process_segmentation(threshold_range, image, update_status):
        print(threshold_range)

        # Fix Volume Orientation
        update_status(text="Rotating views to volume plane...", progress=2)
        manager = slicer.app.layoutManager()
        for name in manager.sliceViewNames():
            widget = manager.sliceWidget(name)
            node = widget.mrmlSliceNode()
            node.RotateToVolumePlane(image)

        # Create segmentation
        update_status(text="Creating segmentation...", progress=5)
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentationNode.CreateDefaultDisplayNodes()
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(image)
        segmentId = segmentationNode.GetSegmentation().AddEmptySegment("Bone")
        segmentationNode.GetSegmentation().GetSegment(segmentId).SetColor([0.9, 0.8, 0.7])

        # Create segment editor to get access to effects
        update_status(text="Starting segmentation editor...", progress=6)
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        segmentEditorWidget.setSegmentationNode(segmentationNode)
        segmentEditorWidget.setMasterVolumeNode(image)

        # Threshold
        update_status(text="Processing threshold segmentation...", progress=8)
        segmentEditorWidget.setActiveEffectByName("Threshold")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("MinimumThreshold", str(threshold_range[0]))  # 1460 #1160 # 223
        effect.setParameter("MaximumThreshold", str(threshold_range[1]))
        effect.self().onApply()

        # Smoothing
        update_status(text="Processing smoothing segmentation...", progress=10)
        segmentEditorWidget.setActiveEffectByName("Smoothing")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("SmoothingMethod", "MORPHOLOGICAL_OPENING")
        effect.setParameter("KernelSizeMm", 0.5)
        effect.self().onApply()

        # Islands
        update_status(text="Processing island segmentation...", progress=11)
        segmentEditorWidget.setActiveEffectByName("Islands")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("Operation", "KEEP_LARGEST_ISLAND")
        effect.setParameter("MinimumSize", 1000)
        effect.self().onApply()

        # Crop
        # update_status("Cropping segmentation...")
        # segmentEditorWidget.setActiveEffectByName("Scissors")
        # effect = segmentEditorWidget.activeEffect()
        # effect.setParameter("MinimumThreshold", "223")
        # effect.setParameter("MaximumThreshold", "3071")
        # effect.self().onApply()

        # Clean up
        update_status(text="Cleaning up...", progress=13)
        segmentEditorWidget.setActiveEffectByName(None)
        slicer.mrmlScene.RemoveNode(segmentEditorNode)

        # Make segmentation results visible in 3D and set focal
        update_status(text="Rendering...", progress=15)
        segmentationNode.CreateClosedSurfaceRepresentation()

        # Make sure surface mesh cells are consistently oriented
        update_status(text="Retrieving surface mesh...", progress=18)
        if slicer.app.majorVersion == 4 and slicer.app.minorVersion <= 10:
            polyData = segmentationNode.GetClosedSurfaceRepresentation(segmentId)
        else:
            polyData = vtk.vtkPolyData()
            segmentationNode.GetClosedSurfaceRepresentation(segmentId, polyData)
        return polyData

    @staticmethod
    def rainfall_quad_cast(poly_data, dimensions, ray_direction, precision, region_of_interest, update_status):
        # configure ray direction
        dimensions = dimensions[::-1]
        negated = 1 if ray_direction in [RayDirection.R, RayDirection.A, RayDirection.S] else -1
        castIndex = None
        if ray_direction is RayDirection.R or ray_direction is RayDirection.L: castIndex = 0
        elif ray_direction is RayDirection.A or ray_direction is RayDirection.P: castIndex = 1
        elif ray_direction is RayDirection.S or ray_direction is RayDirection.I: castIndex = 2
        castVector = [0.0, 0.0, 0.0]; castVector[castIndex] = 1.0 * negated
        castPlaneIndices = [0, 1, 2]; castPlaneIndices.remove(castIndex)
        preciseHorizontalBounds, preciseVerticalBounds = int(float(dimensions[castPlaneIndices[0]]) / float(precision)), int(float(dimensions[castPlaneIndices[1]]) / float(precision))

        def build_ray(i, j):
            start = [None, None, None]
            start[castIndex] = dimensions[castIndex] * negated
            start[castPlaneIndices[0]] = -dimensions[castPlaneIndices[0]]/2.0 + i*precision
            start[castPlaneIndices[1]] = -dimensions[castPlaneIndices[1]]/2.0 + j*precision
            end = start[:]; end[castIndex] = end[castIndex] * -1.0
            return start, end

        # build search tree
        update_status(text="Building intersection object tree...", progress=41)
        bspTree = vtk.vtkModifiedBSPTree()
        bspTree.SetDataSet(poly_data)
        bspTree.BuildLocator()

        # cast rays
        update_status(text="Casting " + str(preciseHorizontalBounds*preciseVerticalBounds) + " rays downward...", progress=42); startTime = time.time()
        points, temporaryHitPoint = vtk.vtkPoints(), [0.0, 0.0, 0.0]
        hitPointMatrix = [[None for i in range(preciseHorizontalBounds)] for j in reversed(range(preciseVerticalBounds))]
        for i in reversed(range(preciseVerticalBounds)):
            for j in range(preciseHorizontalBounds):
                start, end = build_ray(i, j)
                res = bspTree.IntersectWithLine(start, end, 0, vtk.reference(0), temporaryHitPoint, [0.0, 0.0, 0.0], vtk.reference(0), vtk.reference(0))
                if res != 0 and region_of_interest[0] <= temporaryHitPoint[castIndex] < region_of_interest[1]:
                    temporaryHitPoint[castIndex] += 0.3 * negated  # raised to improve visibility
                    hitPointMatrix[i][j] = HitPoint(points.InsertNextPoint(temporaryHitPoint), temporaryHitPoint[:])

        # form cells
        update_status(text="Forming top layer polygons", progress=64)
        cells = vtk.vtkCellArray()
        for i in range(len(hitPointMatrix)-1):
            for j in range(len(hitPointMatrix[i])-1):
                hitPoints = [hitPointMatrix[i][j], hitPointMatrix[i+1][j], hitPointMatrix[i+1][j+1], hitPointMatrix[i][j+1]]
                if None in hitPoints: continue
                rawNormal = numpy.linalg.solve(numpy.array([hitPoints[0].point, hitPoints[1].point, hitPoints[2].point]), [1, 1, 1])
                hitPointMatrix[i][j].normal = rawNormal / numpy.sqrt(numpy.sum(rawNormal**2))
                v1, v2 = numpy.array(hitPointMatrix[i][j].normal), numpy.array(castVector)
                degrees = numpy.degrees(numpy.math.atan2(numpy.cross(v1, v2).shape[0], numpy.dot(v1, v2)))
                if degrees < 80: cells.InsertNextCell(4, [p.pid for p in hitPoints])
        update_status(text="Finished ray-casting in " + str("%.1f" % (time.time() - startTime)) + "s, found " + str(cells.GetNumberOfCells()) + " cells...", progress=80)

        # build poly data
        topLayerPolyData = vtk.vtkPolyData()
        topLayerPolyData.SetPoints(points)
        topLayerPolyData.SetPolys(cells)
        topLayerPolyData.Modified()
        return topLayerPolyData, [p for d0 in hitPointMatrix for p in d0 if p is not None]

    @staticmethod
    def build_model(poly_data, update_status):
        update_status(text="Rendering top layer...", progress=20)
        modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        modelNode.SetAndObservePolyData(poly_data)
        modelNode.CreateDefaultDisplayNodes()
        modelDisplayNode = modelNode.GetModelDisplayNode()
        modelDisplayNode.SetFrontfaceCulling(0)
        modelDisplayNode.SetBackfaceCulling(0)
        update_status(text="Top layer rendered...", progress=40)
        return modelNode

    @staticmethod
    def determine_cast_direction_index(ray_direction):
        if ray_direction is RayDirection.R or ray_direction is RayDirection.L: return 0
        elif ray_direction is RayDirection.A or ray_direction is RayDirection.P: return 1
        elif ray_direction is RayDirection.S or ray_direction is RayDirection.I: return 2

    @staticmethod
    def ray_cast_color_thickness(poly_data, hit_point_list, ray_direction, dimensions, update_status, gradient_scale_factor=10.0):
        # configure ray direction
        castIndex = BoneThicknessMappingLogic.determine_cast_direction_index(ray_direction)

        update_status(text="Building static cell locator...", progress=81)
        cellLocator = vtk.vtkStaticCellLocator()
        cellLocator.SetDataSet(poly_data)
        cellLocator.BuildLocator()

        total = len(hit_point_list)
        update_status(text="Calculating thickness (may take long)...", progress=82); startTime = time.time()
        skullThicknessScalarArray = vtk.vtkUnsignedCharArray()
        skullThicknessScalarArray.SetName(BoneThicknessMappingType.THICKNESS)
        airCellScalarArray = vtk.vtkUnsignedCharArray()
        airCellScalarArray.SetName(BoneThicknessMappingType.AIR_CELL)

        def calculate_distance(point1, point2):
            d = numpy.linalg.norm(numpy.array((point1[0], point1[1], point1[2])) - numpy.array((point2[0], point2[1], point2[2])))
            d = d*gradient_scale_factor
            return d

        tol, pCoords, subId = 0.000, [0, 0, 0], vtk.reference(0)
        pointsOfIntersection, cellsOfIntersection = vtk.vtkPoints(), vtk.vtkIdList()
        for i, hitPoint in enumerate(hit_point_list):
            stretchFactor = dimensions[castIndex]
            start = [hitPoint.point[0] + hitPoint.normal[0]*stretchFactor, hitPoint.point[1] + hitPoint.normal[1]*stretchFactor, hitPoint.point[2] + hitPoint.normal[2]*stretchFactor]
            end = [hitPoint.point[0] - hitPoint.normal[0]*stretchFactor, hitPoint.point[1] - hitPoint.normal[1]*stretchFactor, hitPoint.point[2] - hitPoint.normal[2]*stretchFactor]
            cellLocator.FindCellsAlongLine(start, end, tol, cellsOfIntersection)
            distances = []
            for cellIndex in range(cellsOfIntersection.GetNumberOfIds()):
                t = vtk.reference(0.0)
                p = [0.0, 0.0, 0.0]
                if poly_data.GetCell(cellsOfIntersection.GetId(cellIndex)).IntersectWithLine(start, end, tol, t, p, pCoords, subId) and 0.0 <= t <= 1.0:
                    distances.append([t, p])
            if len(distances) >= 2:
                distances = sorted(distances, key=lambda kv: kv[0])
                p0, p1, pLast = distances[0][1], distances[1][1], distances[-1][1]
                skullThicknessScalarArray.InsertTuple1(hitPoint.pid, calculate_distance(p0, pLast))
                airCellScalarArray.InsertTuple1(hitPoint.pid, calculate_distance(p0, p1))
            else:
                skullThicknessScalarArray.InsertTuple1(hitPoint.pid, 0)
                airCellScalarArray.InsertTuple1(hitPoint.pid, 0)
            # update rays casted status
            if i % 200 == 0: update_status(text="Calculating thickness (~{0} of {1} rays)".format(i, total), progress=82 + int(round((i*1.0/total*1.0)*18.0)))
        update_status(text="Finished thickness calculation in " + str("%.1f" % (time.time() - startTime)) + "s...", progress=100)
        return skullThicknessScalarArray, airCellScalarArray

    @staticmethod
    def load_color_tables():
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Tables/ThicknessGradient.txt"
        thicknessTable = slicer.util.loadColorTable(path, returnNode=True)[1]
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Tables/AirCellGradient.txt"
        airCellTable = slicer.util.loadColorTable(path, returnNode=True)[1]
        return thicknessTable, airCellTable

    @staticmethod
    def build_color_table(name, table_max):
        table = slicer.vtkMRMLColorTableNode()
        table.SetName(name)
        table.SetHideFromEditors(0)
        table.SetTypeToFile()
        table.NamesInitialisedOff()
        table.SetNumberOfColors(table_max)
        table.GetLookupTable().SetTableRange(0, table_max)
        table.NamesInitialisedOn()
        slicer.mrmlScene.AddNode(table)
        return table

    @staticmethod
    def build_color_tables(minmax_thickness, minmax_air_cell, gradient_scale_factor=10.0):
        def calculate_and_set_colour(table, index, hue=0.0, sat=1.0, val=1.0):
            rgb = colorsys.hsv_to_rgb(hue, sat, val)
            table.SetColor(index, str(index/gradient_scale_factor) + ' mm', rgb[0], rgb[1], rgb[2], 1.0)

        def p(lhs, rhs, base, right_mod=1.0):
            return float(lhs-base)/float((rhs-base)*right_mod)

        # thickness table
        ix = [int(i) for i in [minmax_thickness[0]*gradient_scale_factor, (minmax_thickness[1])*gradient_scale_factor + 1]]
        thicknessTable = BoneThicknessMappingLogic.build_color_table('ThicknessColorMap', ix[-1])
        for i in range(ix[0], ix[-1]): calculate_and_set_colour(thicknessTable, i, hue=p(i, ix[-1], ix[0]) * 0.278, sat=0.9, val=0.9)

        # air cell table
        ix = [int(i) for i in [minmax_air_cell[0]*gradient_scale_factor, (minmax_air_cell[1])*gradient_scale_factor + 1]]
        airCellTable = BoneThicknessMappingLogic.build_color_table('AirCellColorMap', ix[-1])
        for i in range(ix[0], ix[-1]): calculate_and_set_colour(airCellTable, i, hue=0.696 - p(i, ix[-1], ix[0]) * 0.571, sat=0.9, val=0.9)

        return thicknessTable, airCellTable

    @staticmethod
    def set_scalar_colour_bar_state(state, color_node_id=None):
        colorWidget = slicer.modules.colors.widgetRepresentation()
        ctkBar = slicer.util.findChildren(colorWidget, name='VTKScalarBar')[0]
        ctkBar.setDisplay(state)
        if state is 0 or color_node_id is None: return
        slicer.util.findChildren(colorWidget, 'ColorTableComboBox')[0].setCurrentNodeID(color_node_id)
        slicer.util.findChildren(colorWidget, 'UseColorNameAsLabelCheckBox')[0].setChecked(True)


class SkullThicknessMappingTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_SkullThicknessMapping1()

    def test_SkullThicknessMapping1(self):
        pass
