def tv_distance(p, q):
    """
    Calculate Total Variation Distance between two probability distributions.
    p, q: Dictionaries mapping states (keys) to probabilities (values).
    """
    keys = set(p.keys()) | set(q.keys())
    return 0.5 * sum(abs(p.get(k,0) - q.get(k,0)) for k in keys)
