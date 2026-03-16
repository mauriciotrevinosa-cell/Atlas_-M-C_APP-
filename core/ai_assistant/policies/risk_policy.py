class RiskPolicy:
    """
    Assesses global risks for tasks before they are executed by the Orchestrator.
    """

    # Extremely dangerous keywords we forbid parsing in Phase 1
    FORBIDDEN_KEYWORDS = [
        "rm -rf", "drop table", "delete from", "truncate table", 
        "os.system", "subprocess.call", "shutil.rmtree"
    ]

    def evaluate_risk(self, objective: str, inputs: dict) -> str:
        """
        Returns 'low', 'medium', 'high', or 'critical' depending on task payload.
        """
        payload = (objective + " " + str(inputs)).lower()

        # Check for catastrophic actions
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in payload:
                return "critical"

        # Check for broad modifications
        if "refactor entire system" in payload or "rewrite all" in payload:
            return "high"

        # Check for standard bug fixes or small module implementations
        if "implement" in payload or "fix" in payload:
            return "medium"

        # Default reading/planning tasks
        return "low"
