# Blender DirectX importer
import os
import sys
bl_info = {
    "name": "Import 7.62 HC file (.act) with weights",
    "description": "Doesn't work with binaries, only with txt. To export object you should enter edit mode and select all verticies. The object must have a UV unwrap and there must be one texture in the scene, otherwise you will get an error.",
    "author": "Export script by kosi maz, fixed and adjusted by abb_228",
    "version": (1, 0),
    "blender": (2, 83, 0),
    "location": "File > Import/Export > 7.62 HC ACT (.x)",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",  # COMMUNITY is default anyway though
    "category": "Import-Export"
    # I commented undocumented settings. -Poikilos
    # "api": 42615,
    # "dependencies": "",
}
import bpy
import bmesh
import bpy_extras

from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
import mathutils
from mathutils import *
from math import radians


#thanks to https://blender.stackexchange.com/questions/49341/how-to-get-the-uv-corresponding-to-a-vertex-via-the-python-api
def uv_from_vert_first(uv_layer, v):
    for l in v.link_loops:
        uv_data = l[uv_layer]
        return uv_data.uv
    return None


def uv_from_vert_average(uv_layer, v):
    uv_average = Vector((0.0, 0.0))
    total = 0.0
    for loop in v.link_loops:
        uv_average += loop[uv_layer].uv
        total += 1.0

    if total != 0.0:
        return uv_average * (1.0 / total)
    else:
        return None
        
        
def read_some_data(context, filepath, use_some_setting):
    print("running read_some_data...")
    f = open(filepath, 'r', encoding='utf-8')
    data = f.read()
    f.close()

    
    print("Importing {}...\n".format(filepath))
    # would normally load the data here
    # print(data)
    
    #ищем материал
    start = data.find('Material')
    tempdata = data[start:]
    end = tempdata.find('{')
    materialname = tempdata[8:end]
    materialname = materialname.strip()
    
    start = tempdata.find('TextureFilename')
    tempdata = tempdata[start:]
    start = tempdata.find('{')+1
    end = tempdata.find(';')
    texturename = tempdata[start:end]
    texturename = texturename.strip()
    texturename = texturename.replace('"','')
    
    print("Found material named \"{0}\" with texture \"{1}\".\n".format(materialname,texturename))
    
    #ищем меш
    start = tempdata.find(';')
    tempdata = tempdata[start:]
    start = tempdata.find('Mesh')
    tempdata = tempdata[start:]
    end = tempdata.find('{')
    meshname = tempdata[4:end]
    meshname = meshname.strip()
    
    print("Found mesh named \"{}\".\n".format(meshname))
    
    print("Now reading vertices and faces...\n") #блять
    
    #reading vertices
    
    tempdata = tempdata[end+1:]
    end = tempdata.find(';')
    totalvertices = tempdata[0:end]
    totalvertices = totalvertices.strip()
    
    print("Total vertices: {}\n".format(totalvertices))
    
    #creating vertex matrix
    
    verts = []
    tempdata = tempdata[end+1:]
    
    while tempdata.find(';;')>0:
        vertsline = ()
        for i in range(3):
            end = tempdata.find(';')
            endofverts = tempdata.find(';;')
            vertstring = float((tempdata[0:end]).strip())
            vertsline = vertsline + (vertstring,)
            if end!=endofverts:
                tempdata = tempdata[end+1:]
            else:
                tempdata = tempdata[end:]
        verts.append(vertsline)
        if tempdata.find(';;')>0:
            tempdata = tempdata[(tempdata.find(','))+1:]
        else:
            tempdata = tempdata[(tempdata.find(';;'))+2:]
            break
            
    print("Vertex matrix has been built.\n")
    
    #reading faces
        
    end = tempdata.find(';')
    totalfaces = tempdata[0:end]
    totalfaces = totalfaces.strip()
    tempdata = tempdata[end+1:]
    
    print("Total faces: {}\n".format(totalfaces))
    
    #creating faces matrix
    
    faces = []
    
    while tempdata.find(';\n')>0:
        vertsline = ()
        end = (tempdata.find(';'))
        facenumber = tempdata[0:end]
        facenumber = int(facenumber.strip()) #number of faces in line, why not?
        tempdata = tempdata[end+1:]

        endofline = tempdata.find('\n')
        endoffaces = tempdata.find(';\n')
        line = ""
        
        line = tempdata[0:endofline-1]
        
        if endofline==endoffaces+1:
            tempdata = tempdata[endofline-1:]
        else:
            tempdata = tempdata[endofline:]
            
            
        #now parse the line
        
        line = line.split(',')
        
        for k in line:
            tzfind = k.find(";") #for different syntaxis with  3;0,2,1;, instead of  3;0,2,1,
            if tzfind>-1:
                k = k[0:tzfind]
            vertsline = vertsline + (int(k),)
        
        faces.append(vertsline)
        if tempdata.find(';\n')==0:
            tempdata = tempdata[(tempdata.find(';\n'))+1:]
            break
            
    print("Faces matrix has been built.\n")
    
    print("Now creating object...\n")    
    
    mesh = bpy.data.meshes.new(meshname)

    bm = bmesh.new()

    sys_matrix = Matrix()
    
    #sys_matrix @= Matrix.Rotation(radians(90), 4, 'X')
    sys_matrix @= Matrix.Scale(-1, 4, Vector((0, 0, 1)))
        
    for v_co in verts:
        vert = bm.verts.new(v_co)
        vert.co = vert.co @ sys_matrix

    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        try:
            bm.faces.new([bm.verts[i] for i in f_idx])
        except:
            # face already exists
            print(f_idx)
            
    bm.to_mesh(mesh)
    mesh.update()

    from bpy_extras import object_utils
    ob = object_utils.object_data_add(bpy.context, mesh, None)

    print("Object created.\n")
    
    #ob.rotation_euler[0] = radians(90)
    
    print("Importing mesh material list...\n")
    
    start = tempdata.find('MeshMaterialList')
    tempdata = tempdata[start:]
    start = tempdata.find(';')+1 #skip number of materials, of course it is one
    tempdata = tempdata[start:]
    end = tempdata.find(';')
    totalfaces = tempdata[0:end]
    totalfaces = totalfaces.strip()
    tempdata = tempdata[end+1:]
    
    print("Number of faces: {}".format(totalfaces))
    
    #creating array just in case
    
    mesh_materials = []
    
    end = tempdata.find(';')
    row = tempdata[0:end]
    
    row = row.split(',\n')
    
    for k in row:
        mesh_materials.append(int(k))
        
    print("Appended materials: {}\n".format(len(mesh_materials)))
    
    #now apply materials to the object
    
    # Get material
    mat = bpy.data.materials.get(materialname)
    tex = bpy.data.textures.get(texturename, 'NONE')
    if mat is None:
        # create material
        mat = bpy.data.materials.new(materialname)
        tex = bpy.data.textures.new(texturename, 'NONE')

    # Assign it to object
    if ob.data.materials:
        # assign to 1st material slot
        ob.data.materials[0] = mat
    else:
        # no slots
        ob.data.materials.append(mat)
    
    print("Importing mesh texture coordinates...\n")
    
    start = tempdata.find('MeshTextureCoords')
    tempdata = tempdata[start:]
    start = tempdata.find('{')+1
    tempdata = tempdata[start:]
    end = tempdata.find(';')
    totalfaces = tempdata[0:end]
    totalfaces = totalfaces.strip()
    tempdata = tempdata[end+1:]
    
    print("Number of faces: {}\n".format(totalfaces))
    
    mesh_textures = []
    
    end = tempdata.find(';;') #end of chunk
    tc_data = tempdata[0:end]
    
    mt_temp = tc_data.split(';,')
    
    for line in mt_temp:
        mt_line_tuple = ()
        mt_line_array = line.split(';')
        for coord in mt_line_array:
            mt_line_tuple = mt_line_tuple + (float(coord),)
        mt_line_array=list(mt_line_tuple)
        mesh_textures.append(mathutils.Vector((mt_line_array[0],-mt_line_array[1])))
        
    print("Mesh textures matrix created.\n")
    
    print("UV coords...")
        
    newuvs = []
    for face in faces:
        for vertex in face:
            newuvs.append(mesh_textures[vertex])
            #print(mesh_textures[vertex])

    kek = mesh.uv_layers.new()
    
    print("Number of vectors: {}".format(len(mesh_textures)))
    print("Number of newuvs: {}".format(len(newuvs)))
    
    for i, twofloats in enumerate(newuvs):
        try:
            kek.data[i].uv = [twofloats[0],twofloats[1]+1]
        except:
            print(twofloats)
        
        
    #just in case, seems like normals are not used at all
    """
    print("And now mesh normals...\n")
    
    start = tempdata.find('MeshNormals')
    tempdata = tempdata[start:]
    start = tempdata.find('{')+1
    tempdata = tempdata[start:]
    end = tempdata.find(';')
    totalfaces = tempdata[0:end]
    totalfaces = totalfaces.strip()
    tempdata = tempdata[end+1:]
    
    print("Number of normals: {}\n".format(totalfaces))
    
    mesh_normals = []
    
    end = tempdata.find(';;') #end of chunk
    mn_data = tempdata[0:end]
    
    mn_temp = mn_data.split(';,')
    
    for line in mn_temp:
        mn_line_tuple = ()
        mt_line_array = line.split(';')
        for coord in mt_line_array:
            mn_line_tuple = mn_line_tuple + (float(coord),)
        mesh_normals.append(mn_line_tuple)
        
    print("Normals matrix created.\n")
    """
    
    print("Reading and applying vertex weights...\n")
    
    
    
    while tempdata.find('SkinWeights')>-1:
        array_of_index = []
        array_of_weight = []
        start = tempdata.find('SkinWeights')
        tempdata = tempdata[start:]
        start = tempdata.find("\"")+1
        tempdata = tempdata[start:]
        groupname = tempdata[0:tempdata.find("\"")]
        print("Found group of vertex with name \"{}\"".format(groupname))
        start = tempdata.find("\";")+2
        tempdata = tempdata[start:]
        end = tempdata.find(";")
        totalvertices = tempdata[0:end]
        totalvertices = int(totalvertices.strip())
        print("Vertices in group: {}".format(totalvertices))
        
        if totalvertices>0:
            tempdata = tempdata[end+1:]
            end = tempdata.find(';')
            row_of_index = tempdata[0:end]
            array_of_index = row_of_index.split(',\n')
            array_of_index = [int(k) for k in array_of_index]
            tempdata = tempdata[end+1:]
            row_of_weight = tempdata[0:tempdata.find(';')]
            array_of_weight = row_of_weight.split(',\n')
            array_of_weight = [float(k) for k in array_of_weight]
        else:
            print("Vertex group \"{}\" is empty".format(groupname))
    
        print("Got the arrays. Commence with creating a group...") #if the group is empty we need to assign it anyways for proper export later
        vertexgroup = ob.vertex_groups.new(name=groupname)
        
        for i, vertex in enumerate(array_of_index):
            vertexgroup.add([vertex], array_of_weight[i], 'REPLACE')
            
        print("Group \"{}\" was created and vertices were assigned".format(groupname))
        
    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportSomeData(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Some Data"

    # ImportHelper mixin class uses this
    filename_ext = ""

    filter_glob: StringProperty(
        default="*",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        return read_some_data(context, self.filepath, self.use_setting)


# main exporting function
def act_exporter(context, filepath, set_axis, set_type):

    set_axis = set_axis
    set_type = set_type

    print("\n\n################")
    print("preparing system matrix...")
    # Creating new matrix for conversing axis
    sys_matrix = Matrix()
    if set_axis:
        #sys_matrix @= Matrix.Rotation(radians(90), 4, 'X')
        sys_matrix @= Matrix.Scale(-1, 4, Vector((0, 0, 1)))

        if set_type == 'ADDON':
            print("export as ADDON")
        else:
            print("export as WEAPON")
    print("done!\n\n")
    
    mesh_obj = context.object
    mesh = context.active_object.data

    # Creating duplicated vertex for each face - I get this from DirectX exporter
    # не надо, брат... по ходу всё не так
    print("preparing mesh data...")
    new_vertices = tuple()
    for v in mesh.vertices:
        new_vertices = new_vertices + (v,)
    #for p in mesh.polygons:
        #new_vertices += tuple(mesh.vertices[i] for i in p.vertices)
    print(str(len(new_vertices)))

    new_polygons = mesh.polygons
    
    #for p in mesh.polygons:
        #new_polygons.append(p.vertices)
    
    Index = 0
    #for p in mesh.polygons:
        #new_polygons.append(tuple(range(Index, Index + len(p.vertices))))
        #Index += len(p.vertices)
    #print(str(len(new_polygons)))
    print("done!\n\n")

    print("opening file...")
    file = open(filepath, 'w', encoding='utf-8')
    print("done!\n\n")

    print("start writing Header...")
    file.write("\
xof 0302txt 0032\n\
template XSkinMeshHeader {\n\
 <3cf169ce-ff7c-44ab-93c0-f78f62d172e2>\n\
 WORD nMaxSkinWeightsPerVertex;\n\
 WORD nMaxSkinWeightsPerFace;\n\
 WORD nBones;\n\
}\n\n\
template VertexDuplicationIndices {\n\
 <b8d65549-d7c9-4995-89cf-53a9a8b031e3>\n\
 DWORD nIndices;\n\
 DWORD nOriginalVertices;\n\
 array DWORD indices[nIndices];\n\
}\n\n\
template SkinWeights {\n\
 <6f0d123b-bad2-4167-a0d0-80224f25fabb>\n\
 STRING transformNodeName;\n\
 DWORD nWeights;\n\
 array DWORD vertexIndices[nWeights];\n\
 array FLOAT weights[nWeights];\n\
 Matrix4x4 matrixOffset;\n\
}\n\n\
Header {\n\
 1;\n\
 0;\n\
 1;\n\
}\n\n\
")
    print("done!\n\n")

    print("writing materials...")
    for mat in mesh.materials:
        file.write("Material {0} ".format(mat.name))
        file.write("{\n\
 0.588000, 0.588000, 0.588000, 1.000000;;\n\
 17.000000;\n\
 0.900000, 0.900000, 0.900000;;\n\
 0.000000, 0.000000, 0.000000;;\n\
")
        file.write(" TextureFilename {\n")
        file.write('  "{0}";\n'.format(bpy.data.textures[0].name))
        file.write(" }\n}\n\n")
    print("done!\n\n")

    print("writing mesh...")
    file.write("Mesh {} ".format(mesh.name))
    file.write("{\n")

    print("vertices...")
    vertex_count = len(new_vertices)
    file.write(" {0};\n".format(vertex_count))
    for index, vertex in enumerate(new_vertices):
        v_co = vertex.co @ sys_matrix # flipping axis here
        file.write(" {0:6f};{1:6f};{2:6f};".format(v_co[0], v_co[1], v_co[2]))
        
        if index == vertex_count - 1:
            file.write(";\n\n")
        else:
            file.write(",\n")
    print("done!")

    print("faces...")
    face_count = len(mesh.polygons)
    file.write("  {0};\n".format(face_count))
    for f_index, face in enumerate(mesh.polygons):
        file.write("  {0};".format(len(face.vertices)))
        # Changing from RightHanded system to LeftHanded
        file.write("{0},{1},{2}".format(face.vertices[0], face.vertices[2], face.vertices[1]))
        if f_index == face_count - 1:
            file.write(";\n\n")
        else:
            file.write(",\n")
    print("done!")
    
    print("material list...")
    file.write(" MeshMaterialList {\n")
    file.write("  {0};\n".format(len(mesh.materials)))
    file.write("  {0};\n".format(face_count))
    for index, face in enumerate(mesh.polygons):
        file.write("  {0}".format(face.material_index))
        if index == face_count -1:
            file.write(";\n")
        else:
            file.write(",\n")
    for mat in mesh.materials:
        file.write("  {")
        file.write("{}".format(mat.name))
        file.write("}\n")
    file.write(" }\n")
    print("done!")#
    

    print("uv coords...")
    uv_coords = mesh.uv_layers.active.data
    
    
    #eg : [ [v0x,v0y] ,[v1x,v1y] , [vnx , vny] ] <- [ v0x,v0y,v1x,v1y,vnx,vny ]
    #а конвертировать?
    
    """
    newuvs = []
    for face in faces:
        for vertex in face:
            newuvs.append(mesh_textures[vertex])
            #print(mesh_textures[vertex])

    kek = mesh.uv_layers.new()
    
    for i, twofloats in enumerate(newuvs):
        print(twofloats)
        kek.data[i].uv = twofloats
    """
    
    """
    newuvs = []
    
    for vector in mesh_obj.data.uv_layers.active.data:
        newuvs.append(vector.uv)
        print(vector.uv)
    
    for p in mesh.polygons:
            for loop in p.loop_indices:
                uv=mesh.uv_layers[0].data[loop].uv
                newuvs.append(uv)
    """
    
    file.write(" MeshTextureCoords {\n")
        
    """
    for idx, face in enumerate(mesh.polygons):
        for vertex in face.vertices:
            print("NIGGER {}".format(vertex))
            if not vertex in verticesdone:            
                verticesdone.append(vertex)            
                olduvs.append(mesh_obj.data.uv_layers.active.data[idx].uv)
    """
    
    
    """
    numvert = 0
    for face in mesh.polygons:
        numvert += len(face.vertices)
    file.write("  {0};\n".format(numvert))
    numfaces = len(mesh.polygons)
    counter = -1
    co = 0
    for face in mesh.polygons:
        counter += 1
        co += 1
        for n in range(len(face.vertices)):
            file.write("{0};{1};".format(mesh_obj.data.uv_layers.active.data[counter].uv[n][0], -mesh_obj.data.uv_layers.active.data[counter].uv[n][1]))
            if co == numfaces:
                if n == len(face.vertices)-1:
                    file.write(";\n")
                else:
                    file.write(",\n")
            else:
                file.write(",\n")
    """
    
    
    newuvs = []
    
    totalnumbers = len(mesh.vertices)
    file.write("  {0};\n".format(totalnumbers))
    
    bm = bmesh.from_edit_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active    
        
    for idx, vertex in enumerate(bm.verts):
        uv_first = uv_from_vert_first(uv_layer, vertex)
        newuvs.append([uv_first[0],uv_first[1]])
        file.write("{0};{1};".format(round(uv_first[0],6),round((-uv_first[1]+1),6)))
        if idx == totalnumbers-1:
            file.write(";\n")
        else:
            file.write(",\n")
        
    file.write(" }\n\n")
    print("done!")
    
    print("normals")
    
    file.write("MeshNormals {\n")
    
    maxvert = len(mesh.vertices)
    
    file.write(" {};\n".format(maxvert))    
    
    for idx, vertex in enumerate(mesh.vertices):
        file.write("{0};{1};{2};".format(round(vertex.normal[0],6),round(vertex.normal[1],6),round(vertex.normal[2]*-1,6)))
        #file.write("{0};{1};{2};".format(-0,-0,-0))
        if idx == maxvert-1:
            file.write(";\n")
        else:
            file.write(",\n")
    
    
    print("faces...")
    face_count = len(mesh.polygons)
    file.write("  {0};\n".format(face_count))
    for f_index, face in enumerate(mesh.polygons):
        file.write("  {0};".format(len(face.vertices)))
        # Changing from RightHanded system to LeftHanded
        file.write("{0},{1},{2}".format(face.vertices[0], face.vertices[2], face.vertices[1]))
        if f_index == face_count - 1:
            file.write(";\n\n")
        else:
            file.write(",\n")
    
    file.write("}\n\n")		
 
    print("and now the skinning")
    file.write("XSkinMeshHeader {\n3;\n9;\n49;\n}\n\n")
    
    vgroups = mesh_obj.vertex_groups;
    
    mdic = dict({
    
    "Bip01": "-0.000003,-2.092602,-0.000000,0.0,-0.000000,0.000000,2.092602,0.0,2.092602,-0.000003,0.000000,0.0,0.104637,-0.000004,-1.865520,1.0",
    "Bip01 Footsteps": "-2.092602,0.000000,0.000000,0.0,0.000000,0.000000,2.092602,0.0,0.000000,-2.092602,0.000000,0.0,-0.000004,-0.104637,-0.031457,1.0",
    "Bip01 Pelvis": "-0.000000,0.000000,-0.045175,0.0,0.068518,-0.000028,-0.000000,0.0,0.000055,0.034995,0.000000,0.0,-0.067715,0.001781,-0.000000,1.0",
    "Bip01 Spine": "-0.000000,0.000000,-0.045017,0.0,0.077002,-0.000028,-0.000000,0.0,0.000061,0.034872,0.000000,0.0,-0.079995,0.001776,-0.000000,1.0",
    "Bip01 Spine1": "0.000000,0.000000,-0.046078,0.0,0.068507,0.000639,0.000000,0.0,-0.001251,0.034989,0.000000,0.0,-0.077767,0.001029,-0.000000,1.0",
    "Bip01 Spine2": "0.000000,0.000000,-0.045823,0.0,0.068507,0.000625,0.000000,0.0,-0.001251,0.034212,0.000000,0.0,-0.087767,0.001010,-0.000000,1.0",
    "Bip01 Neck": "0.000000,0.000000,-0.051281,0.0,0.087975,0.001076,0.000000,0.0,-0.001606,0.058938,0.000000,0.0,-0.125550,0.001745,-0.000000,1.0",
    "Bip01 Head": "-0.000000,0.000000,-0.045022,0.0,0.041669,0.000000,-0.000000,0.0,-0.000000,0.041669,0.000000,0.0,-0.064159,0.002405,-0.000000,1.0",
    "Bip01 HeadNub": "-0.000000,0.000001,-0.360174,0.0,0.360174,0.000000,-0.000000,0.0,-0.000000,0.360174,0.000001,0.0,-0.641007,0.020792,-0.000001,1.0",
    "Bip01 L Clavicle": "-0.073809,0.000000,0.000000,0.0,-0.000000,-0.000519,0.036665,0.0,-0.000000,-0.027258,-0.000699,0.0,-0.003253,-0.000774,-0.052327,1.0",
    "Bip01 L UpperArm": "-0.023514,0.000000,-0.018755,0.0,-0.025366,0.000000,0.017386,0.0,-0.000000,-0.024646,-0.000000,0.0,0.031953,-0.001369,-0.028161,1.0",
    "Bip01 L ForeArm": "-0.023926,-0.003239,-0.021573,0.0,-0.025810,-0.003494,0.019998,0.0,0.007134,-0.023502,-0.000000,0.0,0.022733,0.001718,-0.032393,1.0",
    "Bip01 L Hand": "-0.069459,0.069669,-0.012888,0.0,-0.074930,-0.064603,-0.013792,0.0,0.020711,-0.000074,-0.093118,0.0,0.036966,0.104631,0.006723,1.0",
    "Bip01 L Finger0": "0.034783,-0.359675,-0.115943,0.0,-0.291909,-0.086187,0.149542,0.0,0.144681,-0.087421,0.329593,0.0,0.302776,-0.114819,-0.224139,1.0",
    "Bip01 L Finger01": "-0.054906,-0.351704,-0.115943,0.0,-0.223411,0.035141,0.149542,0.0,0.082051,-0.139665,0.329593,0.0,0.179721,-0.224305,-0.224139,1.0",
    "Bip01 L Finger0Nub": "-0.329436,-1.406815,-0.463771,0.0,-1.340464,0.140565,0.598169,0.0,0.492306,-0.558662,1.318370,0.0,1.018323,-0.897222,-0.896554,1.0",
    "Bip01 L Finger1": "-0.152264,0.263787,-0.063536,0.0,-0.238527,-0.174431,-0.066303,0.0,0.084095,-0.017138,-0.303101,0.0,0.127783,0.330359,0.037754,1.0",
    "Bip01 L Finger11": "-0.045737,0.303806,-0.063536,0.0,-0.217953,-0.076111,-0.066303,0.0,0.057265,-0.047034,-0.303101,0.0,0.168427,0.267003,0.037754,1.0",
    "Bip01 L Finger1Nub": "-0.274422,1.215225,-0.254143,0.0,-1.307720,-0.304443,-0.265214,0.0,0.343588,-0.188138,-1.212405,0.0,0.950560,1.068010,0.151015,1.0",
    "Bip01 L Finger2": "-0.169632,0.292631,-0.004574,0.0,-0.204825,-0.242491,-0.004934,0.0,0.019015,-0.001511,-0.093951,0.0,0.086483,0.412280,0.001931,1.0",
    "Bip01 L Finger21": "-0.070481,0.357799,-0.004574,0.0,-0.198677,-0.127678,-0.004934,0.0,0.013865,-0.010713,-0.093951,0.0,0.135513,0.349902,0.001931,1.0",
    "Bip01 L Finger2Nub": "-0.422888,1.431197,-0.018295,0.0,-1.192060,-0.510713,-0.019736,0.0,0.083191,-0.042852,-0.375804,0.0,0.753079,1.399610,0.007722,1.0",
    "LHAND": "-0.588918,0.799109,0.120836,0.0,-0.790398,-0.600679,0.120230,0.0,0.168660,-0.024703,0.985365,0.0,0.384605,1.050291,-0.060631,1.0",
    "Bip01 R Clavicle": "0.073809,0.000000,-0.000000,0.0,-0.000000,-0.000519,-0.036665,0.0,0.000000,-0.027258,0.000699,0.0,-0.003252,-0.000774,0.052327,1.0",
    "Bip01 R UpperArm": "0.023514,0.000000,-0.018755,0.0,-0.025366,0.000000,-0.017386,0.0,0.000000,-0.024646,-0.000000,0.0,0.031953,-0.001369,0.028161,1.0",
    "Bip01 R ForeArm": "0.023926,0.003239,-0.021573,0.0,-0.025810,-0.003494,-0.019998,0.0,0.007134,-0.023502,-0.000000,0.0,0.022733,0.001718,0.032393,1.0",
    "Bip01 R Hand": "0.069459,-0.069669,-0.012888,0.0,-0.074930,-0.064603,0.013792,0.0,0.020711,-0.000074,0.093118,0.0,0.036966,0.104631,-0.006723,1.0",
    "Bip01 R Finger0": "-0.034784,0.359676,-0.115942,0.0,-0.291909,-0.086187,-0.149542,0.0,0.144681,-0.087420,-0.329593,0.0,0.302776,-0.114817,0.224138,1.0",
    "Bip01 R Finger01": "0.054906,0.351704,-0.115942,0.0,-0.223411,0.035141,-0.149542,0.0,0.082051,-0.139664,-0.329593,0.0,0.179721,-0.224304,0.224138,1.0",
    "Bip01 R Finger0Nub": "0.329434,1.406817,0.463768,0.0,-1.340464,0.140565,0.598169,0.0,0.492307,-0.558658,1.318372,0.0,1.018325,-0.897216,-0.896552,1.0",
    "Bip01 R Finger1": "0.171725,-0.252051,-0.062603,0.0,-0.230234,-0.191535,0.067533,0.0,0.086788,-0.009386,0.303024,0.0,0.107666,0.337800,-0.039734,1.0",
    "Bip01 R Finger11": "0.060873,-0.298923,-0.062603,0.0,-0.213430,-0.096593,0.067533,0.0,0.060141,-0.040229,0.303024,0.0,0.154409,0.281971,-0.039734,1.0",
    "Bip01 R Finger1Nub": "0.365241,-1.195691,0.250411,0.0,-1.280578,-0.386373,-0.270131,0.0,0.360849,-0.160914,-1.212096,0.0,0.866451,1.127885,0.158935,1.0",
    "Bip01 R Finger2": "0.169369,-0.292464,-0.006168,0.0,-0.204319,-0.242689,0.006654,0.0,0.025643,-0.002018,0.093754,0.0,0.086162,0.412361,-0.002550,1.0",
    "Bip01 R Finger21": "0.070317,-0.357514,-0.006168,0.0,-0.198338,-0.128111,0.006654,0.0,0.018702,-0.014429,0.093754,0.0,0.135289,0.350136,-0.002550,1.0",
    "Bip01 R Finger2Nub": "0.421903,-1.430057,0.024672,0.0,-1.190028,-0.512443,-0.026614,0.0,0.112211,-0.057715,-0.375014,0.0,0.751737,1.400542,0.010199,1.0",
    "RHAND": "-0.773398,-0.126314,-1.282656,0.0,1.271271,0.171536,-0.783424,0.0,-0.212215,1.487927,-0.018571,0.0,-0.725015,-0.116404,1.514703,1.0",
    "BACKPOINT_H": "-0.601587,0.101228,-0.792369,0.0,0.110545,0.992943,0.042924,0.0,-0.791123,0.061770,0.608532,0.0,-0.045087,-1.424806,0.065194,1.0",
    "LEFTSIDE_H": "-0.372426,0.093110,-0.923380,0.0,0.095426,0.993522,0.061696,0.0,-0.923142,0.065137,0.378899,0.0,0.006535,-1.170461,-0.032525,1.0",
    "Bip01 L Thigh": "-0.001608,-0.000000,0.020342,0.0,-0.027298,0.002371,-0.001186,0.0,0.002739,0.023634,0.000119,0.0,0.024319,-0.000932,0.003008,1.0",
    "Bip01 L Calf": "-0.001362,-0.000276,0.023712,0.0,-0.023595,-0.002363,-0.001383,0.0,-0.002375,0.023634,0.000139,0.0,0.012315,0.001545,0.003506,1.0",
    "Bip01 L Foot": "-0.000000,-0.000000,0.125016,0.0,-0.103274,-0.000000,-0.000000,0.0,-0.000000,0.056233,0.000000,0.0,0.011552,0.003140,0.017628,1.0",
    "Bip01 L Toe0": "-0.000000,-0.000000,0.117005,0.0,-0.000000,0.179155,0.000000,0.0,0.147020,0.000000,0.000000,0.0,-0.012706,-0.002693,0.016499,1.0",
    "Bip01 L Toe0Nub": "-0.000001,-0.000000,-0.468019,0.0,-0.000000,0.716619,-0.000000,0.0,0.882120,0.000000,-0.000001,0.0,-0.136238,-0.010773,-0.065995,1.0",
    "Bip01 R Thigh": "0.001608,-0.000000,0.020342,0.0,-0.027298,0.002371,0.001186,0.0,0.002739,0.023634,-0.000119,0.0,0.024319,-0.000932,-0.003008,1.0",
    "Bip01 R Calf": "0.001362,0.000276,0.023712,0.0,-0.023595,-0.002363,0.001383,0.0,-0.002375,0.023634,-0.000139,0.0,0.012315,0.001545,-0.003506,1.0",
    "Bip01 R Foot": "-0.000000,-0.000000,0.125016,0.0,-0.103274,-0.000000,-0.000000,0.0,-0.000000,0.056233,0.000000,0.0,0.011552,0.003140,-0.017628,1.0",
    "Bip01 R Toe0": "-0.000000,-0.000000,0.117005,0.0,-0.000000,0.179155,0.000000,0.0,0.147020,0.000000,0.000000,0.0,-0.012706,-0.002693,-0.016498,1.0",
    "Bip01 R Toe0Nub": "-0.000001,-0.000000,0.468019,0.0,-0.000000,0.716619,0.000000,0.0,0.882120,0.000000,0.000001,0.0,-0.136238,-0.010773,-0.065993,1.0"
    
    }) 
    
            
    for i, group in enumerate(vgroups):
        vertex_array_newindex = []
        vertex_array_weight = []
        vertex_count = int
        vertex_count = 0
        file.write("SkinWeights {1}\n    \"{0}\";\n".format(group.name, "{"))
        for k, vertex in enumerate(new_vertices):
            if group.index in [m.group for m in vertex.groups]:
                #vertex_count = vertex_count + 1
                if (group.weight(vertex.index)>0):
                    vertex_count = vertex_count + 1
                    vertex_array_newindex.append(k)
                    vertex_array_weight.append(round(group.weight(vertex.index),6))
                #file.write("{}: ".format(k))
                #file.write("{}\n".format(group.weight(vertex.index)))
        file.write("    {};\n".format(len(vertex_array_newindex)))
        inx = int
        inx = 0;
        for a in vertex_array_newindex:
            inx += 1
            if inx<(vertex_count):
                file.write("    {},\n".format(a))
            else:
                file.write("    {};\n".format(a))
            
        print(format(group.name))
        print(inx)
        print(vertex_count)
        
        inx = 0;
        for a in vertex_array_weight:
            file.write("    {}".format(a))
            inx += 1
            if inx<(vertex_count):
                file.write(",\n")
            else:
                file.write(";\n")
        file.write("{};;\n".format(mdic[group.name]))
        file.write("}\n\n")
        
        
    

    file.write("}\n")
    print("whole mesh - done!\n\n")

    print("closing file...")
    file.close()
    print("done!\n\n")


class ExportToActFile(Operator, ExportHelper):
    """Export selected object to 7.62 HC .ACT file."""
    bl_idname = "export_test.export_to_act"
    bl_label = "Export To ACT File"

    # ExportHelper mixin class uses this
    filename_ext = ""

    filter_glob = StringProperty(
            default="*",
            options={'HIDDEN'},
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    set_axis = BoolProperty(
            name="Converse Axis",
            description="Converse axis from Blender RightHanded to DirectX LeftHanded.",
            default=True,
            )

    set_type = EnumProperty(
            name="Export as:",
            description="",
            items=(('WEAPON', "Weapon", "Choose to export weapons."),
                   ('ADDON', "Attachment", "Choose to export addon attachment.")),
            default='WEAPON',
            )

    def execute(self, context):
        act_exporter(context, self.filepath, self.set_axis, self.set_type)
        return {'FINISHED'}
        
        

# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="7.62 HC mesh (.act)")
    
def menu_func_export(self, context):
    self.layout.operator(ExportToActFile.bl_idname, text="7.62 HC mesh (.act)")


def register():
    bpy.utils.register_class(ExportToActFile)
    bpy.utils.register_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportToActFile)
    bpy.utils.unregister_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_test.some_data('INVOKE_DEFAULT')





