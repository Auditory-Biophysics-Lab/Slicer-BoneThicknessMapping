<img alt='logo' src='https://github.com/Auditory-Biophysics-Lab/SlicerBoneThicknessMappingExtension/blob/master/BoneThicknessMapping/Resources/Icons/logo.png?raw=true' height="200">

# Bone Thickness Mapping Slicer Module

*Developed by HML & SKA Auditory Medical Biophysics Lab at Western University, London, ON, CA*

## About
This [3D Slicer](https://www.slicer.org/) module calculates bone thickness of a volume and overlays a gradient map (with legend) over the segmented volume in 3D.

## Algorithm Procedure
1. Convert input volume to Slicer segmentation
2. Threshold, smooth, and apply island-removal on segmentation
3. Cast a grid of rays in one direction to collect the points representing the surface of the bone
4. Iterate through the retrieved surface mesh, casting a ray through the bone segmentation perpendicular to the bone surface
5. Calculate thickness using bone intersection points
6. Render thickness map with a gradient map on the surface of the bone model

## Basic Usage 
1. Open module via Modules>Shape Analysis>ABL Thickness Mapping in 3D Slicer
2. Using the input volume selector, select a volume representing a bone scan
3. (Optional) Configure the mapping using the module UI
4. Click 'Execute'

## Screenshot
![Screenshot](https://github.com/Auditory-Biophysics-Lab/SlicerBoneThicknessMappingExtension/blob/master/Screenshot.PNG?raw=true)

## Installation
1. Download repository project folder
2. Open 3D Slicer and navigate to the module 'Extension Wizard' (Modules>Developer Tools>Extension Wizard)
3. Click 'Select Extension'
4. Navigate to the repository project folder
5. The module will now be accessible via Modules>Shape Analysis>Thickness Mapping
