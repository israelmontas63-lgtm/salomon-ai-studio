# -*- coding: utf-8 -*-


def test_coolsol_pro_finalize_build():
    from cognicion.core_deployment_finalizer import CoolsolProDeployment

    result = CoolsolProDeployment().finalize_build()
    assert result["ok"] is True
    assert result["status"] == "PRODUCTION_READY"
    assert "BUILD_SUCCESSFUL" in result["message"]
