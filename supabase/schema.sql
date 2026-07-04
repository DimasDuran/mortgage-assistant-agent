-- Vera schema for Supabase Postgres (multi-tenant).
-- Run this once in the Supabase SQL editor (or via the CLI) before serving.
-- Each application is stored as JSONB so the URLA sections can fill progressively.

-- Organizations (tenants): each lender is one organization.
create table if not exists organizations (
    id          text primary key,
    name        text not null,
    created_at  timestamptz not null default now()
);

create table if not exists applications (
    id              text primary key,
    organization_id text references organizations (id),
    status          text not null default 'draft',
    data            jsonb not null,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- For existing deployments created before multi-tenancy.
alter table applications add column if not exists organization_id text;

-- Tenant-scoped lookups (list a lender's cases) hit this index.
create index if not exists applications_organization_id_idx
    on applications (organization_id);

-- Keep updated_at fresh on every change.
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists applications_set_updated_at on applications;

create trigger applications_set_updated_at
    before update on applications
    for each row execute function set_updated_at();
