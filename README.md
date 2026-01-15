# 🌊 FlowPose

**Fluid IK/FK Posing with Real-Time Collisions for Blender**

Pose Pulling
![0116](https://github.com/user-attachments/assets/bfe93e0b-449b-4a65-bd4f-b81bea8dcdb6)


Collisions
![0116(1)](https://github.com/user-attachments/assets/d54f43fb-43b1-4670-8837-0c78cdb158ab)


FlowPose is a workflow-enhancing add-on for Blender that bridges the gap between Forward Kinematics (FK) and Inverse Kinematics (IK). It allows you to drag any bone with "Smart Pull" physics, slide limbs against surfaces without clipping, and pose complex chains—**like tails, spines, and tentacles**—effortlessly.

## ✨ Key Features

### 1. Smart Pull (The "Tail" Solver) 🦎

This is where FlowPose shines. If you pull an FK bone beyond its length, the add-on propagates that movement up the parent chain.

* **Perfect for Tails & Tentacles:** You don't need a complex rig. Just grab the tip of a tail and drag it; the rest of the tail follows naturally in a smooth curve.
* **Spine Adjustment:** Quickly adjust posture by pulling the chest bone, and the lower spine will accommodate the movement.
* **Drawing poses** Move the mouse instead of individual bones to the motion you were imaginating, disable the pull if you want 👍


### 2. Real-Time Surface Collision 🧱

Never clip through the floor again. FlowPose uses BVH Tree calculations to detect the environment in real-time.

* **Wall Sliding:** Push a hand against a wall, and it will slide along the surface rather than passing through it.
* **Auto-Orientation:** The bone can automatically rotate to align with the surface normal (e.g., a palm flattening against a table).
**WARNING** It collides on bones, so change the surface distance if the mesh is clipping a bit

### 3. Smart Filtering

Choose exactly what your rig interacts with:

* **All Visible:** Interact with everything in the scene.
* **Collection:** Only interact with objects in a specific "Environment" collection.
* **Single Object:** (Default) Interact with a specific floor or prop.

---

## 🎮 Controls

Once the add-on is installed, select a bone in **Pose Mode**:

| Key | Action |
| --- | --- |
| **D** | **Activate FlowPose** (Enter modal state) |
| **Mouse Move** | Drag the bone naturally |
| **LMB** | Confirm Pose |
| **RMB / Esc** | Cancel |

---

## 🛠️ Installation

1. Download the `FlowPose.py` file.
2. Open Blender and go to **Edit > Preferences > Add-ons**.
3. Click **Install...** and select the file.
4. Enable the checkbox for **Animation: FlowPose**.
5. Find the settings in the **N-Panel > FlowPose** tab.

---

## 💡 Usage Tips

* **For Tails:** Enable "Auto Pull" in the sidebar. Select the very tip of the tail and just drag it around. The add-on will rotate the parent bones to follow your mouse, creating a smooth, organic curve instantly.
* **For Walking:** Set the Collision Source to your "Floor" object. When you place a foot IK controller, it will stop exactly at the floor surface.

## 📝 License

GPL-3.0 (Standard Blender Add-on License)
