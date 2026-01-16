bl_info = {
    "name": "FlowPose",
    "author": "MR",
    "version": (1, 4),
    "blender": (3, 0, 0),
    "location": "View3D > 'D' Key",
    "description": "FK/IK System with Multi-Bone Limits and Collision",
    "category": "Animation",
}

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector, Quaternion, Matrix
from bpy.props import FloatProperty, BoolProperty, EnumProperty, PointerProperty, IntProperty, StringProperty, CollectionProperty
from mathutils.bvhtree import BVHTree

addon_keymaps = []

# --- DATA STRUCTURES ---
class FlowStopBoneItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Bone Name")

class CollisionSettings(bpy.types.PropertyGroup):
    enabled: BoolProperty(
        name="Enable Collisions",
        default=True
    )
    collision_source: EnumProperty(
        name="Collision Source",
        description="Which objects block movement?",
        items=[
            ('ALL', "All Visible", "All visible objects (Except active)"),
            ('COLLECTION', "Collection", "Objects in a specific collection (Environment)"),
            ('OBJECT', "Single Object", "A specific single object (e.g. Floor)"),
        ],
        default='OBJECT'
    )
    col_collection: PointerProperty(
        name="Environment Collection",
        type=bpy.types.Collection,
        description="Collection containing walls/floors"
    )
    col_object: PointerProperty(
        name="Environment Object",
        type=bpy.types.Object,
        description="Single object serving as wall/floor"
    )
    offset_distance: FloatProperty(
        name="Surface Distance",
        description="Safety distance (Thickness)",
        default=0.05,
        min=0.001, max=1.0
    )
    slide_friction: FloatProperty(
        name="Friction",
        description="0 = Slide, 1 = Stick to wall",
        default=0.1,
        min=0.0, max=1.0
    )
    align_smooth: FloatProperty(
        name="Surface Smoothing",
        description="Alignment speed (0.1 = slow, 1.0 = instant)",
        default=0.5, min=0.0, max=1.0
    )
    align_axis: EnumProperty(
        name="Surface Facing Axis",
        items=[
            ('POS_Y', "+Y (Tip)", "Bone points towards the wall"),
            ('NEG_Y', "-Y (Root)", "Base points towards the wall"),
            ('POS_X', "+X (Side)", "+X side faces the wall"),
            ('NEG_X', "-X (Palm)", "-X side faces the wall"),
            ('POS_Z', "+Z (Top)", "Top side faces the wall"),
            ('NEG_Z', "-Z (Bottom)", "Bottom side faces the wall"),
        ],
        default='NEG_X'
    )

# --- OPERATORS ---
class OT_FlowPose(bpy.types.Operator):
    bl_idname = "pose.flow_pose"
    bl_label = "FlowPose"
    bl_options = {'REGISTER', 'UNDO'}

    mouse_pos = Vector((0, 0))

    current_bone = None
    ik_constraint = None
    ik_target_bone = None
    bvh_trees = {}
    
    # Cache stop bones names for performance
    stop_bone_names = []

    def invoke(self, context, event):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Pose Mode required!")
            return {'CANCELLED'}

        self.build_collision_cache(context)
        
        # Cache the stop list
        self.stop_bone_names = [item.name for item in context.scene.flow_stop_bones]

        bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))
        self.current_bone = context.active_pose_bone
        if not self.current_bone:
             return {'CANCELLED'}

        self.find_ik_controller(context)
        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def build_collision_cache(self, context):
        self.bvh_trees = {}
        settings = context.scene.collision_settings
        if not settings.enabled:
            return

        candidates = []
        active_obj = context.active_object

        if settings.collision_source == 'ALL':
            candidates = [o for o in context.scene.objects
                          if o.type == 'MESH' and o.visible_get() and o != active_obj]

        elif settings.collision_source == 'COLLECTION':
            if settings.col_collection:
                candidates = [o for o in settings.col_collection.objects
                              if o.type == 'MESH' and o.visible_get() and o != active_obj]

        elif settings.collision_source == 'OBJECT':
            if settings.col_object and settings.col_object.type == 'MESH':
                candidates = [settings.col_object]

        for obj in candidates:
            try:
                depsgraph = context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(depsgraph)
                mesh = obj_eval.to_mesh()
                bvh = BVHTree.FromPolygons(
                    [v.co for v in mesh.vertices],
                    [p.vertices for p in mesh.polygons]
                )
                self.bvh_trees[obj.name] = (bvh, obj.matrix_world.copy())
                obj_eval.to_mesh_clear()
            except Exception as e:
                print(f"FlowPose Cache Error {obj.name}: {e}")

    def solve_collision(self, start_pos, end_pos, context):
        if not self.bvh_trees or not context.scene.collision_settings.enabled:
            return end_pos, Vector((0,0,1)), False

        final_pos = end_pos
        settings = context.scene.collision_settings
        offset = settings.offset_distance
        move_vec = end_pos - start_pos
        move_len = move_vec.length
        move_dir = move_vec.normalized() if move_len > 0.00001 else Vector((0,0,1))

        hit_occured = False
        closest_dist = float('inf')
        best_hit_info = None
        last_normal = Vector((0,0,1))

        for name, (bvh, mat) in self.bvh_trees.items():
            mat_inv = mat.inverted()
            local_start = mat_inv @ start_pos
            local_dir = (mat_inv.to_3x3() @ move_dir).normalized()
            scale_fac = (mat_inv.to_3x3() @ move_vec).length / (move_len if move_len > 0 else 1)
            local_dist = move_len * scale_fac

            loc, normal, idx, dist = bvh.ray_cast(local_start, local_dir, local_dist)
            if loc:
                world_loc = mat @ loc
                world_normal = (mat.to_3x3() @ normal).normalized()
                world_dist = (world_loc - start_pos).length
                if world_dist < closest_dist:
                    closest_dist = world_dist
                    best_hit_info = (world_loc, world_normal)
                    hit_occured = True
                    last_normal = world_normal

        if hit_occured:
            hit_pos, hit_norm = best_hit_info
            base_pos = hit_pos + (hit_norm * offset)
            remaining_dist = move_len - closest_dist
            if remaining_dist > 0:
                remainder = move_dir * remaining_dist
                slide = remainder - (remainder.dot(hit_norm) * hit_norm)
                slide *= (1.0 - settings.slide_friction)
                final_pos = base_pos + slide
            else:
                final_pos = base_pos

        pos_to_check = final_pos
        corrected_prox = pos_to_check
        hit_proximity = False

        for name, (bvh, mat) in self.bvh_trees.items():
            mat_inv = mat.inverted()
            local_pt = mat_inv @ pos_to_check
            loc, normal, idx, dist = bvh.find_nearest(local_pt, offset * 2.0)
            if loc:
                world_surf = mat @ loc
                world_norm = (mat.to_3x3() @ normal).normalized()
                real_dist = (world_surf - pos_to_check).length
                if real_dist < offset:
                    vec_to = (pos_to_check - world_surf).normalized()
                    if vec_to.dot(world_norm) < 0.1:
                        corrected_prox = world_surf + (world_norm * offset)
                        last_normal = world_norm
                        hit_proximity = True

        return corrected_prox, last_normal, (hit_occured or hit_proximity)

    def find_ik_controller(self, context):
        self.ik_constraint = None
        self.ik_target_bone = None
        if not context.scene.flow_use_ik: return

        target_bone = self.current_bone
        armature = context.active_object

        for const in target_bone.constraints:
             if const.type == 'IK' and const.target == armature and const.subtarget:
                 self.ik_constraint = const
                 self.ik_target_bone = armature.pose.bones.get(const.subtarget)
                 return

        for p_bone in armature.pose.bones:
            for const in p_bone.constraints:
                if const.type == 'IK' and const.target == armature and const.subtarget:
                    chain_len = const.chain_count
                    curr = p_bone
                    limit = chain_len if chain_len > 0 else 999
                    count = 0
                    while curr and count < limit:
                        if curr == target_bone:
                            self.ik_constraint = const
                            self.ik_target_bone = armature.pose.bones.get(const.subtarget)
                            return
                        curr = curr.parent
                        count += 1

    def modal(self, context, event):
        context.area.tag_redraw()
        if event.type == 'MOUSEMOVE':
            self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            if not event.alt and not event.shift and not event.ctrl:
                if self.ik_target_bone and context.scene.flow_use_ik:
                    self.process_ik_fk_logic(context)
                else:
                    self.process_standard_fk(context)

        # Toggle Lock Selection with 'L'
        if event.type == 'L' and event.value == 'PRESS':
            context.scene.flow_lock_selection = not context.scene.flow_lock_selection
            state = "LOCKED" if context.scene.flow_lock_selection else "UNLOCKED"
            self.report({'INFO'}, f"Bone Selection: {state}")

        if event.type in {'D', 'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self.finish(context)
            return {'FINISHED'}

        if context.active_pose_bone != self.current_bone:
            self.current_bone = context.active_pose_bone
            self.find_ik_controller(context)

        return {'PASS_THROUGH'}

    def finish(self, context):
        self.bvh_trees.clear()

    def process_smart_pull(self, context, active_bone, mouse_vector, distance_gap):
        obj = context.active_object
        region = context.region
        rv3d = context.region_data
        chain_limit = context.scene.flow_pull_chain_depth
        stiffness_base = context.scene.flow_pull_stiffness
        curr_parent = active_bone.parent
        count = 0

        while curr_parent and count < chain_limit:
            parent_head_3d = obj.matrix_world @ curr_parent.head
            parent_head_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, parent_head_3d)
            if not parent_head_2d: break

            effector_3d = obj.matrix_world @ active_bone.tail
            effector_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, effector_3d)
            if not effector_2d: break

            vec_to_effector = effector_2d - parent_head_2d
            vec_to_mouse = self.mouse_pos - parent_head_2d
            angle = vec_to_effector.angle_signed(vec_to_mouse)
            damping = stiffness_base + (count * 0.15)
            if damping > 0.95: damping = 0.95
            angle *= (1.0 - damping) * 0.5

            view_z = rv3d.view_matrix.inverted().to_3x3().col[2]
            view_z_local = obj.matrix_world.inverted().to_3x3() @ view_z
            rot_mat = Quaternion(view_z_local, -angle).to_matrix().to_4x4()

            original_matrix = curr_parent.matrix.copy()
            curr_parent.matrix = Matrix.Translation(curr_parent.head) @ rot_mat @ Matrix.Translation(-curr_parent.head) @ curr_parent.matrix
            context.view_layer.update()

            new_tip_pos = obj.matrix_world @ active_bone.tail
            corrected_tip = self.solve_collision(effector_3d, new_tip_pos, context)[0]

            if (corrected_tip - new_tip_pos).length > 0.01:
                curr_parent.matrix = original_matrix

            curr_parent = curr_parent.parent
            count += 1

        context.view_layer.update()

    def process_standard_fk(self, context):
        bone = self.current_bone
        if not bone: return
        obj = context.active_object
        region = context.region
        rv3d = context.region_data

        head_3d = obj.matrix_world @ bone.head
        head_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, head_3d)
        if not head_2d: return

        tail_3d = obj.matrix_world @ bone.tail
        tail_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, tail_3d)
        if not tail_2d: return

        mouse_vec = self.mouse_pos - head_2d
        current_bone_vec = tail_2d - head_2d
        bone_len_2d = current_bone_vec.length
        angle = current_bone_vec.angle_signed(mouse_vec)
        angle *= context.scene.flow_sensitivity

        view_z = rv3d.view_matrix.inverted().to_3x3().col[2]
        view_z_local = obj.matrix_world.inverted().to_3x3() @ view_z
        rot_mat = Quaternion(view_z_local, -angle).to_matrix().to_4x4()

        temp_matrix = Matrix.Translation(bone.head) @ rot_mat @ Matrix.Translation(-bone.head) @ bone.matrix
        temp_tail_world = obj.matrix_world @ temp_matrix @ Vector((0, bone.length, 0))

        if context.scene.collision_settings.enabled:
            real_tail_world, hit_normal, is_colliding = self.solve_collision(tail_3d, temp_tail_world, context)
            bone.matrix = temp_matrix
            context.view_layer.update()

            if is_colliding:
                align_axis_enum = context.scene.collision_settings.align_axis
                align_factor = context.scene.collision_settings.align_smooth
                vec_lookup = {
                    'POS_Y': Vector((0,1,0)), 'NEG_Y': Vector((0,-1,0)),
                    'POS_X': Vector((1,0,0)), 'NEG_X': Vector((-1,0,0)),
                    'POS_Z': Vector((0,0,1)), 'NEG_Z': Vector((0,0,-1))
                }
                vec_local_target = vec_lookup.get(align_axis_enum, Vector((0,1,0)))
                curr_bone_rot_world = (obj.matrix_world @ bone.matrix).to_quaternion()
                current_axis_vec_world = curr_bone_rot_world @ vec_local_target
                rot_diff = current_axis_vec_world.rotation_difference(hit_normal)
                correction_quat = Quaternion((1, 0, 0, 0)).slerp(rot_diff, align_factor)
                pivot = obj.matrix_world @ bone.head
                mat_trans = Matrix.Translation(pivot) @ correction_quat.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
                new_world_mat = mat_trans @ (obj.matrix_world @ bone.matrix)
                bone.matrix = obj.matrix_world.inverted() @ new_world_mat
        else:
            bone.matrix = temp_matrix

        context.view_layer.update()

        dist_vec = self.mouse_pos - head_2d
        
        # --- MULTI-LIMIT LOGIC ---
        # Check if the current bone name is in the stop list
        is_at_stop_bone = bone.name in self.stop_bone_names

        can_descend = True
        if is_at_stop_bone: can_descend = False
        if context.scene.flow_lock_selection: can_descend = False

        if dist_vec.length > bone_len_2d * 1.05:
            if bone.children and dist_vec.length > bone_len_2d * 0.95 and not context.scene.flow_force_pull_mode and can_descend:
                # Slide down to child
                self.current_bone = bone.children[0]
                context.active_object.data.bones.active = self.current_bone.bone
                self.find_ik_controller(context)
            else:
                # Pull Logic
                if context.scene.flow_enable_pull:
                    self.process_smart_pull(context, bone, dist_vec, dist_vec.length - bone_len_2d)

    def process_ik_fk_logic(self, context):
        obj = context.active_object
        region = context.region
        rv3d = context.region_data
        ik_bone = self.ik_target_bone

        current_ik_world = obj.matrix_world @ ik_bone.matrix.translation

        mouse_3d = view3d_utils.region_2d_to_location_3d(
            region, rv3d,
            self.mouse_pos,
            current_ik_world 
        )

        desired_ik_world = mouse_3d
        final_ik_world = desired_ik_world
        
        if context.scene.collision_settings.enabled:
            final_ik_world, _, _ = self.solve_collision(current_ik_world, desired_ik_world, context)

        mw_inverse = obj.matrix_world.inverted()
        new_local_translation = mw_inverse @ final_ik_world

        new_matrix = ik_bone.matrix.copy()
        new_matrix.translation = new_local_translation
        ik_bone.matrix = new_matrix
        context.view_layer.update()

        pivot_3d = obj.matrix_world @ self.current_bone.head
        pivot_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, pivot_3d)
        tail_3d = obj.matrix_world @ self.current_bone.tail
        tail_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, tail_3d)

        if pivot_2d and tail_2d:
            current_bone_len_2d = (tail_2d - pivot_2d).length
            mouse_dist_from_pivot = (self.mouse_pos - pivot_2d).length

            if mouse_dist_from_pivot > current_bone_len_2d * 1.1:
                mouse_vec = self.mouse_pos - pivot_2d
                if context.scene.flow_enable_pull:
                    self.process_smart_pull(context, self.current_bone, mouse_vec, 0)

# --- PICKER & LIST OPERATORS ---

class OT_FlowPickStopBone(bpy.types.Operator):
    bl_idname = "pose.flow_pick_stop_bone"
    bl_label = "Pick Stop Bone"
    bl_description = "Click on a bone in the 3D View to add it to the Stop List"

    def modal(self, context, event):
        context.area.tag_redraw()
        
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            context.window.cursor_modal_restore()
            return {'CANCELLED'}
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Perform selection to find bone under mouse
            try:
                bpy.ops.view3d.select(location=(event.mouse_region_x, event.mouse_region_y))
                bone = context.active_pose_bone
                if bone:
                    # Check for duplicates
                    existing = [item.name for item in context.scene.flow_stop_bones]
                    if bone.name not in existing:
                        item = context.scene.flow_stop_bones.add()
                        item.name = bone.name
                        self.report({'INFO'}, f"Added {bone.name} to Stop List")
                    else:
                        self.report({'WARNING'}, f"{bone.name} is already in the list")
                else:
                    self.report({'WARNING'}, "No bone selected")
            except Exception as e:
                self.report({'ERROR'}, str(e))
            
            context.window.cursor_modal_restore()
            return {'FINISHED'}
            
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Please enter Pose Mode first")
            return {'CANCELLED'}
        
        context.window.cursor_modal_set('EYEDROPPER')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class OT_FlowRemoveStopBone(bpy.types.Operator):
    bl_idname = "pose.flow_remove_stop_bone"
    bl_label = "Remove Stop Bone"
    bl_description = "Remove this bone from the limit list"
    
    index: IntProperty()

    def execute(self, context):
        context.scene.flow_stop_bones.remove(self.index)
        return {'FINISHED'}

class OT_FlowClearAllStopBones(bpy.types.Operator):
    bl_idname = "pose.flow_clear_all_stop_bones"
    bl_label = "Clear List"
    bl_description = "Clear all stop bones"

    def execute(self, context):
        context.scene.flow_stop_bones.clear()
        return {'FINISHED'}

# --- UI ---
class PT_FlowPosePanel(bpy.types.Panel):
    bl_label = "FlowPose V1.4"
    bl_idname = "PT_FlowPose"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FlowPose'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col_settings = scene.collision_settings

        box = layout.box()
        box.label(text="Animation Mode:", icon='ARMATURE_DATA')
        box.prop(scene, "flow_use_ik", text="IK-FK Hybrid")
        box.prop(scene, "flow_sensitivity", slider=True, text="Sensitivity")

        box = layout.box()
        box.label(text="Smart Pull (Body):", icon='FORCE_MAGNETIC')
        box.prop(scene, "flow_enable_pull", text="Enable Pull")
        col = box.column(align=True)
        col.enabled = scene.flow_enable_pull
        col.prop(scene, "flow_force_pull_mode", text="Force Pull")
        col.prop(scene, "flow_pull_stiffness", slider=True, text="Stiffness")
        col.prop(scene, "flow_pull_chain_depth", text="Chain Depth")
        
        # --- STOP LIST UI ---
        col.separator()
        col.label(text="Stop Limits (Bones):", icon='CANCEL')
        
        row = col.row(align=True)
        row.operator("pose.flow_pick_stop_bone", text="Pick Bone (Click)", icon='EYEDROPPER')
        row.operator("pose.flow_clear_all_stop_bones", text="", icon='TRASH')
        
        if len(scene.flow_stop_bones) > 0:
            list_box = col.box()
            for i, item in enumerate(scene.flow_stop_bones):
                row = list_box.row()
                row.label(text=item.name, icon='BONE_DATA')
                op = row.operator("pose.flow_remove_stop_bone", text="", icon='X')
                op.index = i
        else:
            col.label(text="No limits set (Slides to tip)", icon='INFO')
        # --------------------

        box = layout.box()
        header = box.row()
        header.label(text="Collisions & Filters:", icon='MOD_PHYSICS')
        header.prop(col_settings, "enabled", text="")

        if col_settings.enabled:
            col = box.column(align=True)
            col.prop(col_settings, "collision_source", text="Source")
            if col_settings.collision_source == 'COLLECTION':
                col.prop(col_settings, "col_collection")
            elif col_settings.collision_source == 'OBJECT':
                col.prop(col_settings, "col_object")

            col.separator()
            col.prop(col_settings, "offset_distance")
            col.prop(col_settings, "slide_friction")
            col.prop(col_settings, "align_axis", text="Magnet Axis")

            col.separator()
            col.operator("pose.rebuild_collision_cache", icon='FILE_REFRESH', text="Update Cache")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="[D] Activate | [L] Global Lock")
        col.label(text="RMB / ESC to Cancel")

class OT_RebuildCollisionCache(bpy.types.Operator):
    bl_idname = "pose.rebuild_collision_cache"
    bl_label = "Rebuild Collision Cache"

    def execute(self, context):
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FlowStopBoneItem)
    bpy.utils.register_class(CollisionSettings)
    bpy.types.Scene.collision_settings = PointerProperty(type=CollisionSettings)
    bpy.types.Scene.flow_sensitivity = FloatProperty(name="Sensitivity", default=1.0)
    bpy.types.Scene.flow_use_ik = BoolProperty(name="IK Mode", default=True)
    bpy.types.Scene.flow_pull_stiffness = FloatProperty(name="Pull Stiffness", default=0.5, min=0.0, max=0.99)
    bpy.types.Scene.flow_pull_chain_depth = IntProperty(name="Chain Depth", default=3, min=1, max=10)
    bpy.types.Scene.flow_force_pull_mode = BoolProperty(name="Force Pull", default=False)
    bpy.types.Scene.flow_enable_pull = BoolProperty(name="Auto Pull Enable", default=True)
    
    bpy.types.Scene.flow_lock_selection = BoolProperty(
        name="Lock Selection", 
        default=False, 
        description="Globally prevent automatic bone switching"
    )
    
    # New Collection Property for list
    bpy.types.Scene.flow_stop_bones = CollectionProperty(type=FlowStopBoneItem)

    bpy.utils.register_class(OT_FlowPose)
    bpy.utils.register_class(OT_FlowPickStopBone)
    bpy.utils.register_class(OT_FlowRemoveStopBone)
    bpy.utils.register_class(OT_FlowClearAllStopBones)
    bpy.utils.register_class(OT_RebuildCollisionCache)
    bpy.utils.register_class(PT_FlowPosePanel)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Pose', space_type='EMPTY')
        kmi = km.keymap_items.new(OT_FlowPose.bl_idname, 'D', 'PRESS')
        addon_keymaps.append((km, kmi))

def unregister():
    del bpy.types.Scene.flow_sensitivity
    del bpy.types.Scene.flow_use_ik
    del bpy.types.Scene.collision_settings
    del bpy.types.Scene.flow_pull_stiffness
    del bpy.types.Scene.flow_pull_chain_depth
    del bpy.types.Scene.flow_force_pull_mode
    del bpy.types.Scene.flow_enable_pull
    del bpy.types.Scene.flow_lock_selection
    del bpy.types.Scene.flow_stop_bones

    bpy.utils.unregister_class(PT_FlowPosePanel)
    bpy.utils.unregister_class(OT_RebuildCollisionCache)
    bpy.utils.unregister_class(OT_FlowPickStopBone)
    bpy.utils.unregister_class(OT_FlowRemoveStopBone)
    bpy.utils.unregister_class(OT_FlowClearAllStopBones)
    bpy.utils.unregister_class(OT_FlowPose)
    bpy.utils.unregister_class(CollisionSettings)
    bpy.utils.unregister_class(FlowStopBoneItem)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

if __name__ == "__main__":
    register()
