cmake_minimum_required(VERSION 3.5)

project(ABL Bone Thickness Mapping Thickness Mapping)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/BoneThicknessMapping")
set(EXTENSION_CATEGORY "Shape Analysis")
set(EXTENSION_CONTRIBUTORS "Evan Simpson (HML & SKA Lab, Western University)")
set(EXTENSION_DESCRIPTION "3D Slicer extension that calculates the bone thickness of a volume using VTK ray-casting.")
# set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/ThicknessMapping.png")
# set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/BoneThicknessMapping/Screenshots/1.png")
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
