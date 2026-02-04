from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from ssct_circuits import build_job_bundle
import json, datetime

SHOTS = 1024

def main():
    try:
        service = QiskitRuntimeService()
    except Exception as e:
        print(f"Error connecting to QiskitRuntimeService: {e}")
        print("Please ensure you have saved your IBM Quantum account using: QiskitRuntimeService.save_account(channel='ibm_quantum', token='MY_TOKEN')")
        return

    try:
        backend = service.least_busy(operational=True, simulator=False)
        print(f"Using backend: {backend.name}")
    except Exception as e:
        print(f"Error finding backend: {e}")
        return

    sampler = Sampler(backend=backend)
    circuits = build_job_bundle()

    print(f"Submitting job with {SHOTS} shots...")
    job = sampler.run(circuits, shots=SHOTS)
    print(f"Job ID: {job.job_id()}")
    
    result = job.result()
    print("Job completed.")

    ts = datetime.datetime.utcnow().isoformat()

    # Ensure results directory exists
    import os
    os.makedirs("results", exist_ok=True)

    for i, label in enumerate(["A","B","C"]):
        # Adjust for different result structures if necessary
        # SamplerV2 returns PubResult which contains data
        pub_result = result[i]
        # data.meas is typical for V2, but depends on circuit register name. 
        # Default name is often 'meas' if not specified, or 'c' if classical bit. 
        # Since circuit uses measure([0,1,2], [0,1,2]), classical reg name might be needed.
        # Assuming standard 'meas' for now as per user spec.
        try:
            counts = pub_result.data.meas.get_counts()
        except AttributeError:
             # Fallback if register name is different, though user code implies 'meas'
             # Trying to access the first classical register
             counts = pub_result.data.c.get_counts()


        probs = {k: v/SHOTS for k,v in counts.items()}

        payload = {
            "timestamp_utc": ts,
            "backend": backend.name,
            "shots": SHOTS,
            "theta": ["A","B","C"][i],
            "counts": counts,
            "probabilities": probs
        }

        with open(f"results/qpu_{label}.json", "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Saved results/qpu_{label}.json")

if __name__ == "__main__":
    main()
