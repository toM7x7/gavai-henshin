from pathlib import Path

from henshin.design_coherence import run_design_coherence_audit


def test_design_coherence_audit_reports_current_visual_debt() -> None:
    audit = run_design_coherence_audit(root=Path("."))

    assert audit["ok"] is True
    assert audit["module_count"] == 18
    assert audit["expected_module_count"] == 18

    codes = {finding["code"] for finding in audit["findings"]}
    assert "runtime_texture_path" in codes
    assert "operator_identity_drift" in codes
    assert "canon_fit_drift" in codes

    drift_parts = {finding["part"] for finding in audit["findings"] if finding["code"] == "canon_fit_drift"}
    assert {"left_forearm", "right_forearm", "left_thigh", "right_thigh"}.issubset(drift_parts)


def test_design_coherence_audit_keeps_left_right_pairs_clean() -> None:
    audit = run_design_coherence_audit(root=Path("."))

    pair_findings = [finding for finding in audit["findings"] if finding["code"].startswith("left_right")]
    assert pair_findings == []
