# histmap-autogeoref-tools
This repository contains Python scripts for automating the georeferencing of scanned map images from large, standardized collections of historical maps. As of version 0.2.0-alpha the repository contains scripted processes for facilitating the automated georeferencing of historical Sanborn Fire Insurance maps of areas in the United States using an object detection model that has been trained to identify street intersection locations and associated street labels which can be matched by the georeferencing-automator.py script with street intersection data with geographic coordinates from OpenStreetMap. Historical Sanborn Fire Insurance Maps of Texas that have been successfully georeferenced using this automated process have been published to the Texas GeoData Portal (https://geodata.lib.utexas.edu) where they can be previewed and downloaded by selecting individual maps of interest from the list of results at https://geodata.lib.utexas.edu/?f%5Bdct_creator_sm%5D%5B%5D=Sanborn+Map+Company+%28cartographer%29&f%5Bschema_provider_s%5D%5B%5D=Texas&q=&search_field=all_fields.


## Citing
If citing the software contained in this repository, please use the following citation format:

Shensky, M., Strickland, K., Marden, A., Dubbe, H. 2024. Histmap-AutoGeoRef-Tools [version]. GitHub. [Access date].
https://github.com/utlibraries/histmap-autogeoref-tools.


## Associated Data and Object Detection Model

Associated data and the trained street intersection object detection model for the Texas Sanborn Fire Insurance Map georeferencing project can be accessed at:

Shensky, M., Strickland, K., Marden, A., Dubbe, H. 2024. Data to Support Automated Georeferencing Workflow for Historical Sanborn Fire Insurance Maps of Texas. Dataset. https://doi.org/10.18738/T8/KEE3TT Texas Data Repository, V3, UNF:6:+ZeDaFMzriIBTvSRTR0UcQ== [fileUNF]



## Tools

### custom-object-detection-TF2.ipynb
This notebook runs the process for training the historical Sanborn Fire Insurance Map street intersection object detection model that has been published at https://doi.org/10.18738/T8/KEE3TT.

### georeferenced-map-quality-assessment.py
This script iterates over a directory of json formatted reports generated by georeferencing-automator.py which describe the results obtained for each processed map. The script features adjustable parameters which define criteria that can be used to determine which processed maps were successfully georeferenced according to a set level of accuracy, which maps were georeferenced but ended up with unacceptable levels of distortion, and which maps could not be georeferenced at all.

### georeferencing-automator.py
This script carries out the automated georeferencing workflow by iterating over a directory of Sanborn Fire Insurance scanned map images, detecting the locations of street intersections in the image, matching those intersections with coordinate information contained in the city json file created by street-intersection-data-generator.py, creating ground control points based on the matched street intersection pixel coordinates and geographic coordinates, and then generating a georeferenced geotiff of each map if at least 3 ground control points were successfully identified. The script also generates a report json file for each map that is processed which can be analyzed by the georeferenced-map-quality-assessment.py to gain insight into the results generated by this process.

### prepare-directory-structure.py
This script should be run first to generate all required directories on the local file system that will be used to run the automated georeferencing process.

### street-intersection-data-generator.py
This script generates json formatted data for street intersections of defined cities. The state for which intersection data is pulled is defined using a hardcoded parameter. The specific cities in the defined state for intersection data should be generated are determined by iterating over a directory of Sanborn Fire Insurance map images and pulling the city name from standardized structure of the file name. The script generates a json file with intersection coordinate and street label information for each street intersection in a defined city by pulling that data from OpenStreetMap using the OSMNX package and then saves the data for each city in its own separate json file.

### tf-record-generator.py
This script is used by custom-object-detection-TF2.ipynb to create the train and test record files.


## Contact
For any questions about this repository, please contact utl-gis@austin.utexas.edu
