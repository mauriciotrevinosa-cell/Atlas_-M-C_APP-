import math
from qiskit import QuantumCircuit

def build_ssct(theta0, theta1, theta2):
    qc = QuantumCircuit(3, 3)
    qc.h([0,1,2])
    qc.ry(theta0, 0)
    qc.ry(theta1, 1)
    qc.ry(theta2, 2)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.measure([0,1,2], [0,1,2])
    return qc

def build_job_bundle():
    A = build_ssct(0.0, 0.0, 0.0)
    B = build_ssct(math.pi/3, math.pi/3, math.pi/3)
    C = build_ssct(math.pi/3, -math.pi/3, math.pi/3)
    return [A, B, C]
