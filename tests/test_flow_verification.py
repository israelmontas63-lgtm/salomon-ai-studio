# -*- coding: utf-8 -*-


def test_channel_unification_audit():
    from cognicion.core_flow_verification import ChannelUnificationAuditor

    result = ChannelUnificationAuditor().audit_routing_integrity()
    assert result["ok"] is True
    assert result["status"] == "UNIFIED"
    assert "ROUTING_SUCCESSFUL" in result["message"]
    assert all(f["ok"] for f in result["findings"])
