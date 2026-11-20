from src.property_signin import InfraiClient, MagicLinkRequest, request_magic_link


class FakeClient(InfraiClient):
    def __init__(self):
        super().__init__("test-key")
        self.calls = []

    def passwordless_request(self, email, request_id):
        self.calls.append(("auth.password.reset_request", email, request_id))
        return {"ok": True, "data": {}}

    def send_link(self, email, link, request_id):
        self.calls.append(("email.send", email, link, request_id))
        return {"ok": True, "data": {"message_id": "message-7"}}


def test_maintenance_tenant_gets_property_scoped_link():
    client = FakeClient()
    result = request_magic_link(
        client,
        MagicLinkRequest("sam@example.com", "oak-house", "request-7"),
        "https://example.test/sign-in",
    )

    assert result == result.__class__("sam@example.com", "oak-house", "message-7")
    assert client.calls[0] == ("auth.password.reset_request", "sam@example.com", "request-7")
    assert "request_id=request-7" in client.calls[1][2]
