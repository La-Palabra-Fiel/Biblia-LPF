#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import desk
import server


class ServerSecurityTests(unittest.TestCase):
    def test_production_refuses_missing_security_configuration(self):
        with patch.object(server,"PRODUCTION",True),patch.object(server,"ALLOWED_ORIGINS",set()),patch.object(server,"ALLOWED_HOSTS",set()),patch.object(server,"GATEWAY_SECRET",""),patch.object(server.desk,"load_people",return_value={"Ana":"plaintext"}),patch.dict(os.environ,{},clear=True):
            errors=server.production_configuration_errors()
        self.assertTrue(any("DATA_DIR" in error for error in errors))
        self.assertTrue(any("https://" in error for error in errors))
        self.assertTrue(any("ALLOWED_HOSTS" in error for error in errors))
        self.assertTrue(any("GATEWAY_SECRET" in error for error in errors))
        self.assertTrue(any("plaintext" in error for error in errors))

    def test_complete_production_configuration_passes(self):
        record=desk.hashed_credential("correct horse battery staple")
        with patch.object(server,"PRODUCTION",True),patch.object(server,"ALLOWED_ORIGINS",{"https://review.example.org"}),patch.object(server,"ALLOWED_HOSTS",{"review.example.org"}),patch.object(server,"GATEWAY_SECRET","a"*64),patch.object(server.desk,"load_people",return_value={"Ana":record}),patch.dict(os.environ,{"LBF_TEAM_DATA_DIR":"/private/persistent/team"},clear=True):
            self.assertEqual(server.production_configuration_errors(),[])

    def test_authentication_rate_limit_expires_and_clears(self):
        key="192.0.2.5"
        server.clear_auth_failures(key)
        for _ in range(server.AUTH_FAILURE_LIMIT):
            server.record_auth_failure(key)
        self.assertTrue(server.auth_rate_limited(key))
        server.clear_auth_failures(key)
        self.assertFalse(server.auth_rate_limited(key))


if __name__ == "__main__":
    unittest.main()
