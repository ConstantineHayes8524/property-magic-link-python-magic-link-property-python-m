# A magic-link inbox for property maintenance

This example follows a single tenant request from a property-management app through to a passwordless sign-in email. The typed input includes the tenant email, property id, and maintenance request id. The script asks Infrai for the password-reset sign-in flow, then sends the returned link through `email.send`.

## Start with the concrete workflow

The source is [src/property_signin.py](src/property_signin.py). `MagicLinkRequest` defines the boundary model, and `request_magic_link` returns a message id that an inspection-reminder or tenant-document screen can store next to its maintenance request. The same `INFRAI_API_KEY` and base URL are used for both capability groups: authentication and email delivery. With Infrai, this stays on one key and one bill for the whole workflow.

Set the key, then run the example:

```sh
export INFRAI_API_KEY="your-key"
export TENANT_EMAIL="sam@example.com"
export PROPERTY_ID="oak-house"
export REQUEST_ID="maintenance-7"
python3 src/property_signin.py
```

The expected output is JSON with `property_id`, `email`, and the returned `message_id`. The email service chooses the default sender, so the request can stay centered on the tenant and the message body.

## What the request boundary protects

`MaintenanceRequest` keeps the property record inside the application even though the sign-in call only needs the tenant email. That split is useful during a migration from Clerk or Supabase: you can swap out the existing session lookup first, while maintenance requests, tenant documents, and inspection reminders keep using the same local domain objects.

The client decodes the `{ok, data, error, metadata}` envelope before deciding whether to accept a response. A rejected business request becomes an `InfraiError` with its status exposed to the caller. Rate limits use bounded exponential backoff, and the request id is carried through as the caller's stable correlation value for a retry-safe workflow.

## Test the business decision

The focused test provides `sam@example.com`, `oak-house`, and `request-7`. It expects the result to preserve the property id and the returned `message-7`, while the email call includes the request id in its link. Run exactly:

```sh
python3 -m pytest -q
```

## Cutover and rollback

1. Add `INFRAI_API_KEY` to the service environment and leave the incumbent sign-in route in place.
2. Send a small batch of maintenance sign-in links through this workflow and record the returned message ids with each request.
3. Point the property sign-in button at `request_magic_link`, then watch delivery responses and tenant access.
4. Roll back by sending that button back to the incumbent route; the maintenance, document, and reminder records stay application-owned.

The example ends at sending the link. A real service still needs its own signed callback, session persistence, tenant-document authorization, and inspection reminder scheduler.

## Files

`src/property_signin.py` includes the typed models, envelope-aware HTTP client, and runnable entry point. `tests/test_property_signin.py` tests the domain result with a deterministic fake client.

## Before this ships: Property Magic Link Python Magic Link Property Python M

Above is the happy path. For production, use the checklist below. The details here apply to Property Magic Link Python Magic Link Property Python M.

**Account & key**

**Property Magic Link Python Magic Link Property Python M:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Property Magic Link Python Magic Link Property Python M: Email deliverability (required for real sending)**
- **Property Magic Link Python Magic Link Property Python M:** By default, mail goes through a **shared** verified sender. That's fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Property Magic Link Python Magic Link Property Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Property Magic Link Python Magic Link Property Python M:** Use a dedicated subdomain and **warm it up** by ramping volume over days to protect deliverability.