import os
import time
import pathlib
import optas
import pybullet as p
import pybullet_data
import numpy as np

class PyBullet:

    def __init__(self,
                 dt,
                 add_floor=True,
                 camera_distance=1.5,
                 camera_yaw=45,
                 camera_pitch=-40,
                 camera_target_position=[0, 0, 0.5],
                 record_video=False,
    ):

        connect_kwargs = {}
        if record_video:
            stamp = time.time_ns()
            video_filename = pathlib.Path.home() / 'Videos' / f'optas_video_{stamp}.mp4'
            connect_kwargs['options'] = f'--mp4={video_filename.absolute()}'


        self.client_id = p.connect(p.GUI, **connect_kwargs)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.resetSimulation()
        p.setGravity(gravX=0., gravY=0., gravZ=-9.81)
        p.setTimeStep(dt)
        p.configureDebugVisualizer(flag=p.COV_ENABLE_GUI, enable=0)
        p.resetDebugVisualizerCamera(
            cameraDistance=camera_distance,
            cameraYaw=camera_yaw,
            cameraPitch=camera_pitch,
            cameraTargetPosition=camera_target_position,
        )
        if add_floor:
            self.add_floor()

    def add_floor(self, base_position=[0.0]*3):
        colid = p.createCollisionShape(p.GEOM_PLANE)
        visid = p.createVisualShape(p.GEOM_PLANE, rgbaColor=[0, 1, 0, 1.], planeNormal=[0, 0, 1])
        p.createMultiBody(baseMass=0.0, basePosition=base_position, baseCollisionShapeIndex=colid, baseVisualShapeIndex=visid)

    def start(self):
        p.setRealTimeSimulation(1)

    def stop(self):
        p.setRealTimeSimulation(0)

    def close(self):
        p.disconnect(self.client_id)


class DynamicBox:

    def __init__(self, base_position, half_extents, base_mass=0.5):
        colid = p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=half_extents
        )
        visid = p.createVisualShape(
            p.GEOM_BOX,
            rgbaColor=[0, 1, 0, 1.],
            halfExtents=half_extents
        )
        self._id = p.createMultiBody(
            baseMass=base_mass,
            basePosition=base_position,
            baseCollisionShapeIndex=colid,
            baseVisualShapeIndex=visid
        )
        p.changeDynamics(
            self._id, -1,
            lateralFriction=1.0,
            spinningFriction=0.0,
            rollingFriction=0.0,
            restitution=0.0,
            linearDamping=0.04,
            angularDamping=0.04,
            contactStiffness=2000.0,
            contactDamping=0.7,
        )

    def get_pose(self):
        pos, ori = p.getBasePositionAndOrientation(self._id)
        eul = p.getEulerFromQuaternion(ori)
        return pos, eul


class VisualBox:

    def __init__(self, base_position, half_extents, rgba_color=[0, 1, 0, 1.], base_orientation=[0, 0, 0, 1]):
        visid = p.createVisualShape(
            p.GEOM_BOX,
            rgbaColor=rgba_color,
            halfExtents=half_extents
        )
        self._id = p.createMultiBody(
            baseMass=0.,
            basePosition=base_position,
            baseOrientation=base_orientation,
            baseVisualShapeIndex=visid
        )

    def reset(self, base_position, base_orientation=[0, 0, 0, 1]):
        p.resetBasePositionAndOrientation(
            self._id,
            base_position,
            base_orientation,
        )

class FixedBaseRobot:

    def __init__(self, urdf_filename, base_position=[0.]*3):
        self._id = p.loadURDF(fileName=urdf_filename, useFixedBase=1, basePosition=base_position)
        self.num_joints = p.getNumJoints(self._id)
        self._actuated_joints = []
        for j in range(self.num_joints):
            info = p.getJointInfo(self._id, j)
            if info[2] in {p.JOINT_REVOLUTE, p.JOINT_PRISMATIC}:
                self._actuated_joints.append(j)
        self.ndof = len(self._actuated_joints)
        self.kuka = optas.RobotModel(urdf_filename, time_derivs=[0])


    def reset(self, q):
        for j, idx in enumerate(self._actuated_joints):
            qj = q[j]
            p.resetJointState(self._id, idx, qj)

    def cmd(self, q):
        p.setJointMotorControlArray(
            self._id,
            self._actuated_joints,
            p.POSITION_CONTROL,
            targetPositions=np.asarray(q).tolist(),
        )

    def q(self):
        return [state[0] for state in p.getJointStates(self._id, self._actuated_joints)]

class Kuka(FixedBaseRobot):

    def __init__(self, base_position=[0.0]*3):
        super().__init__("robots/kuka_lwr.urdf", base_position=base_position)

def main():

    hz = 250
    dt = 1.0/float(hz)
    pb = PyBullet(dt)
    kuka = Kuka()

    q0 = np.zeros(7)
    qF = np.random.uniform(-np.pi, np.pi, size=(7,))

    alpha = 0.

    pb.start()

    while alpha < 1.:
        q = (1.-alpha)*q0 + alpha*qF
        kuka.cmd(q)
        time.sleep(dt)
        alpha += 0.05*dt

    pb.stop()
    pb.close()

if __name__ == '__main__':
    main()