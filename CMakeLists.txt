cmake_minimum_required(VERSION 3.5)

project(BoneThicknessMapping)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/Auditory-Biophysics-Lab/SlicerBoneThicknessMappingExtension")
set(EXTENSION_CATEGORY "Shape Analysis")
set(EXTENSION_CONTRIBUTORS "Evan Simpson (HML & SKA Lab, Western University)")
set(EXTENSION_DESCRIPTION "3D Slicer extension that calculates the bone thickness of a volume using VTK ray-casting.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/Auditory-Biophysics-Lab/SlicerBoneThicknessMappingExtension/master/BoneThicknessMapping/Resources/Icons/icon128.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/Auditory-Biophysics-Lab/SlicerBoneThicknessMappingExtension/master/Screenshot.PNG")
set(EXTENSION_DEPENDS "NA")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(BoneThicknessMapping)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
