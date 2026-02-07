# 🌊 FlowPose (**free addon**)

**Fluid FK Posing with Real-Time Collisions for Blender 4.X and 5.X**

**HIGHLY RECCOMENDED FOR FK**

![ezgif-87f101cdfe13c5a3](https://github.com/user-attachments/assets/dc8299fb-f7f8-4769-a00c-06b508654319)

Bone Pulling

![0116](https://github.com/user-attachments/assets/bfe93e0b-449b-4a65-bd4f-b81bea8dcdb6)

Collisions

![0116(1)](https://github.com/user-attachments/assets/d54f43fb-43b1-4670-8837-0c78cdb158ab)

Fast Posing

![0116(2)](https://github.com/user-attachments/assets/0c35e8f0-3adf-4cd1-8eab-cd650f78a692)

Difference with IK

![ezgif-8e553cba4adc14f3](https://github.com/user-attachments/assets/fe44fff5-f02e-487a-8a2d-25227fcea8e2)



FlowPose is a workflow-enhancing add-on for Blender that proposes a new way of posing. It allows you to draw/drag any bone with "Smart Pull" physics, slide limbs against surfaces without clipping, and pose complex chains—**like tails, spines, and tentacles**—effortlessly.

(the rig is **Adjustable Mannequin by Vertex Arcade**)

### 0. The Drawing poses process

Instead of manually rotating each bone: 

**Grab the start of an arm/leg/spine/tail, press D** and **Draw the curve**

(modify **sensitivity and smoothness** as needed)

(you can also **setup multiple stop bones for hands and feets** so that you don't accidently pull fingers for example)

witouth stop bone

![witouth](https://github.com/user-attachments/assets/352a0664-b0be-4910-9e3f-36618b60937c)

with stop bone (at the chest)

![with](https://github.com/user-attachments/assets/066fc379-c616-4002-852f-eab78db2dc1b)

the **pull at the end** acts as an **natural adjustement** of the curve you did

(modify it's **stiffness** and **chain depth** as needed to make the **pull smoother** and **pull more bones**)

(enable **force pull if you only want the pull of the current bone**)

for **collisions** select **an object or a collection** as a parameter first, (all visible is not reccomended)

change the **magnet axis** if you want your bone to rotate a certain way if colliding with something


There is an **IK compatible mode** but it's very **experimental**

**your feedback is very much appreciated**


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

<img width="414" height="658" alt="image" src="https://github.com/user-attachments/assets/1cd22866-b949-42c9-bc24-638d4a53aee8" />



### 1. Smart Pull (The "Tail" Solver) 🦎

This is where FlowPose shines. If you pull an FK bone beyond its length, the add-on propagates that movement up the parent chain.

* **Perfect for Tails & Tentacles:** You don't need a complex rig. Just grab the tip of a tail and drag it; the rest of the tail follows naturally in a smooth curve.
* **Spine Adjustment:** Quickly adjust posture by pulling the chest bone, and the lower spine will accommodate the movement.
* **Natural Drawing Poses:** Move your mouse to trace the motion you imagine—FlowPose handles the bone rotation. Disable "Pull" for precise single-bone control. 👍
* **Custom Chain Limits:** Use the "Stop Bone" picker to set a hard limit (like the hand), preventing the tool from sliding into fingers or unintended bones.




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

---

## 💡 Usage Tips

* **For Tails:** Enable "Auto Pull" in the sidebar. Select the very tip of the tail and just drag it around. The add-on will rotate the parent bones to follow your mouse, creating a smooth, organic curve instantly.
* **For Walking:** Set the Collision Source to your "Floor" object. When you place a foot IK controller, it will stop exactly at the floor surface.


## 📝 License

GPL-3.0 (Standard Blender Add-on License)
