import json
import networkx as nx
import osmnx as ox
import geopandas as gpd
import os
from pyproj import Transformer

#REQUIRED PARAMETERS
#input the state or region to limit results to
state = ""

#input directory
inputdir = ""

#output directory
outputdir = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/geolocated-intersections-separated-by-map"

#limit on number of cities to process
cityprocessinglimit = 1000






# Walk through the input directory containing scanned map files and process each file.
# The logic here will have to be matched to the file name structure
#In this example the file names are txu_sanborn_cityname

citylist = []

for root, dirs, files in os.walk(inputdir):
    # Iterate over each file in the directory
    for f in files:
        # Check if the file is an image with one of the specified extensions
        if f[-3:] == "jpg" or f[-3:] == "png" or f[-3:] == "tif":
            # Format the filename to lowercase and replace hyphens and spaces with underscores
            filename = f.split(".")[0].lower().replace("-","_").replace(" ","_")
            # In this example the filename contains 'txu_sanborn_', remove it and any trailing numbers after '_1'
            if "_" in filename:
                cityname = filename.replace("txu_sanborn_","")
                cityname = cityname.split("_1")[0].replace("_"," ")
            if "_" in cityname:
                cityname = cityname.split("_")[0]
            if cityname not in citylist:
                citylist.append(cityname)

# Activate the line below to limit the number of cities to process
citylist = citylist[:cityprocessinglimit]

#produce a list of unsuccessful cities
unsuccessful_cities = []

print("\n\n" + str(len(citylist)) + " cities identified and added to citylist\n")

# Iterate over the list of cities to process each one
for city in citylist:
    print("Processing city: "+ city.title() + ", " + state)
    try:
        # Define the place query as a dictionary
        place_query = {'city': f"{city}", 'state': state, 'country': "USA"}

        # Get the street network within the city boundaries and project
        G = ox.graph_from_place(place_query, network_type='drive', which_result=1)
        G = ox.project_graph(G)
    except:
        print(f"Error: City '{city}' not found. Skipping.")
        unsuccessful_cities.append(city)
        continue
    # Consolidate intersections to simplify the graph
    ints = ox.consolidate_intersections(G, rebuild_graph=False, tolerance=15, dead_ends=False)
    # Create a GeoDataFrame from the consolidated intersections
    gdf = gpd.GeoDataFrame(ints, columns=['geometry'], crs=G.graph['crs'])
    # Extract X and Y coordinates from the geometry
    X = gdf['geometry'].map(lambda pt: pt.coords[0][0])
    Y = gdf['geometry'].map(lambda pt: pt.coords[0][1])
    # Find the nearest nodes in the graph to the given coordinates
    nodes = ox.nearest_nodes(G, X, Y)

    #get intersection names
    connections = {}
    for n in nodes:
        connections[n] = set([])
        for nbr in nx.neighbors(G, n):
            for d in G.get_edge_data(n, nbr).values():
                if 'name' in d:
                    if type(d['name']) == str:
                        connections[n].add(d['name'])
                    elif type(d['name']) == list:
                        for name in d['name']:
                            connections[n].add(name)
                    else:
                        connections[n].add(None)
                else:
                    connections[n].add(None)

    # print(connections)
    print("    Number of elements in list: " +  str(len(connections)))

    #get intersection coordinates
    intersection_coordinates = {}
    for node in nodes:
        intersection_coordinates[node] = G.nodes[node]['x'], G.nodes[node]['y']

    # print(intersection_coordinates)




    # Define the source and target coordinate systems
    source_crs = G.graph['crs']  # Get the projected CRS from the graph
    target_crs = "EPSG:4326"  # WGS84 (latitude/longitude)

    # Create a transformer object
    transformer = Transformer.from_crs(source_crs, target_crs)

    # Reproject the coordinates in the intersection_coordinates dictionary
    for node, coords in intersection_coordinates.items():
        x, y = coords
        lon, lat = transformer.transform(x, y)
        intersection_coordinates[node] = (lon, lat)

    # print(intersection_coordinates)

    joined_data = {node: {
        "street-labels": connections[node],
        "coordinates": intersection_coordinates.get(node, None)
    } for node in connections}

    # Pad the coordinates to a consistent length (e.g., 6 digits for x and y)
    for node_data in joined_data.values():
        coords = node_data.get("coordinates")
        if coords:
            formatted_coords = f"{coords[0]:06.6f},{coords[1]:06.6f}"  # 6 digits for x,y
            node_data["coordinates"] = formatted_coords

    for node_data in joined_data.values():
        street_labels = list(node_data["street-labels"])  # Convert set to a list
        node_data["street-labels"] = street_labels

    # Replace spaces in city name with underscores for filename
    filename_city = city.replace(" ", "_")

    # Wrap the joined_data in a dictionary with the "street-intersections" label
    wrapped_data = {"street-intersections": list(joined_data.values())}

    # Move the file writing operation inside the loop
    with open(os.path.join(outputdir, f"intersection_data_{filename_city}.json"), "w") as f:
        json.dump(wrapped_data, f, indent=4)
        print("    Intersection data saved to: intersection_data_" + filename_city + ".json\n")


#Print the list of cities that were unsuccessfully processed
print("\n")
print("Cities not found:", unsuccessful_cities)
