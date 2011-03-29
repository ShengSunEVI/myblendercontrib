# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>


bl_info = {
    'name': "Theme manager",
    'author': "Bart Crouch",
    'version': (1, 0, 0),
    'blender': (2, 5, 7),
    'api': 35842,
    'location': "User Preferences > Themes > Header",
    'warning': "",
    'description': "Load or save a custom theme",
    'wiki_url': "http://wiki.blender.org/index.php/Extensions:2.5/Py/"\
        "Scripts/System/Theme_manager",
    'tracker_url': "http://projects.blender.org/tracker/index.php?"\
        "func=detail&aid=26659",
    'category': 'System'}


import bpy
import gzip
from io_utils import ExportHelper, ImportHelper
import pickle


# load operator
class LoadTheme(bpy.types.Operator, ImportHelper):
    bl_idname = "ui.load_theme"
    bl_label = "Load Theme"
    bl_description = "Load a theme from file"
    
    filename_ext = ".blt"
    filter_glob = bpy.props.StringProperty(default="*.blt", options={'HIDDEN'})
    
    def execute(self, context):
        # load file
        try:
            file = gzip.open(self.filepath, mode='r')
            dump = pickle.load(file)
            file.close()
            dump["info"]["script"]
        except:
            self.report("ERROR", "Could not read file")
            return{'CANCELLED'}
        
        # apply theme
        theme = bpy.context.user_preferences.themes["Default"]
        for ts, props in dump["values"].items():
            theme_struct = getattr(theme, ts)
            for prop, val in props.items():
                if type(val) != type({}):
                    setattr(theme_struct, prop, val)
                else:
                    # one level deeper
                    if type(prop) == type(1):
                        # collection property (bone color set)
                        prop_struct = theme_struct[prop]
                    else:
                        prop_struct = getattr(theme_struct, prop)
                    for subprop, subval in val.items():
                        setattr(prop_struct, subprop, subval)
        
        # report to user
        author = dump["info"]["author"]
        theme_name = dump["info"]["theme_name"]
        self.report('INFO', "Loaded " + theme_name + " by " + author)
        
        return{'FINISHED'}


# save operator
class SaveTheme(bpy.types.Operator, ExportHelper):
    bl_idname = "ui.save_theme"
    bl_label = "Save Theme"
    bl_description = "Save the current theme to a .blt file"
    
    filename_ext = ".blt"
    filter_glob = bpy.props.StringProperty(default="*.blt", options={'HIDDEN'})
    author = bpy.props.StringProperty(name="Author",
        default=bpy.context.user_preferences.system.author,
        description="Name of the person who created the theme")
    theme_name = bpy.props.StringProperty(name="Theme name",
        default="",
        description="Name of the theme")
    
    def execute(self, context):
        # create dictionary with all information
        dump = {"info":{}, "values":{}}
        dump["info"]["script"] = bl_info['name']
        dump["info"]["script_version"] = bl_info['version']
        dump["info"]["version"] = bpy.app.version
        dump["info"]["build_revision"] = bpy.app.build_revision
        dump["info"]["author"] = self.author
        dump["info"]["theme_name"] = self.theme_name
        
        # defaults
        if not self.author:
            dump["info"]["author"] = "Unknown"
        if not self.theme_name:
            dump["info"]["theme_name"] = "Custom theme"
        
        # get current theme settings
        theme = bpy.context.user_preferences.themes["Default"]
        theme_structs = [[ts.lower(), getattr(theme, ts.lower())] for ts in \
            bpy.types.Theme.bl_rna.properties['theme_area'].enum_items.keys()]
        for name, ts in theme_structs:
            dump["values"][name] = {}
            if str(type(ts)) == "<class 'bpy_prop_collection'>":
                # bone color sets
                for i, struct in enumerate(ts):
                    dump["values"][name][i] = {}
                    for prop in struct.bl_rna.properties:
                        if prop.identifier == "rna_type":
                            # not a setting, so skip
                            continue
                        val = getattr(ts[i], prop.identifier)
                        if str(type(val)) in ["<class 'bpy_prop_array'>",
                        "<class 'mathutils.Color'>"]:
                            # array
                            dump["values"][name][i][prop.identifier] = [v \
                                for v in val]
                        else:
                            # single value
                            dump["values"][name][i][prop.identifier] = val    
                continue
            for prop in ts.bl_rna.properties:
                if prop.identifier == "rna_type":
                    # not a setting, so skip
                    continue
                val = getattr(ts, prop.identifier)
                if prop.type != 'POINTER':
                    if str(type(val)) in ["<class 'bpy_prop_array'>",
                        "<class 'mathutils.Color'>"]:
                        # array
                        dump["values"][name][prop.identifier] = [v for v in \
                            val]
                    else:
                        # single value
                        dump["values"][name][prop.identifier] = val
                else:
                    # one level deeper
                    dump["values"][name][prop.identifier] = {}
                    for subprop in val.bl_rna.properties:
                        if subprop.identifier == "rna_type":
                            # not a setting, so skip
                            continue
                        subval = getattr(val, subprop.identifier)
                        if subprop.type != 'POINTER':
                            if str(type(subval)) in [\
                            "<class 'bpy_prop_array'>",
                            "<class 'mathutils.Color'>"]:
                                # array
                                dump["values"][name][prop.identifier]\
                                    [subprop.identifier] = [v for v in subval]
                            else:
                                # single value
                                dump["values"][name][prop.identifier]\
                                    [subprop.identifier] = subval
                
        # save to file
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        file = gzip.open(filepath, mode='w')
        pickle.dump(dump, file)
        file.close()
        
        return{'FINISHED'}


# draw function for integration in header
def header_func(self, context):
    if context.user_preferences.active_section == 'THEMES':
        self.layout.separator()
        self.layout.operator("ui.load_theme")
        self.layout.operator("ui.save_theme")


classes = [LoadTheme,
    SaveTheme]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.USERPREF_HT_header.append(header_func)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.types.USERPREF_HT_header.remove(header_func)


if __name__ == "__main__":
    register()