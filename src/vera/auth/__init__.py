"""Authentication and authorization (Supabase Auth).

Accounts are provisioned by invitation: the lender side invites a person to a
case, Supabase emails them a link to set a password, and login returns a JWT.
This package verifies that JWT and enforces role- and application-scoped access.
"""
