create extension if not exists pgcrypto;

create table if not exists public.invitations(
 id uuid primary key default gen_random_uuid(),
 token text unique not null default encode(gen_random_bytes(12),'hex'),
 honoree text not null check(honoree in('candida','alberto')),
 seat_limit integer not null default 1 check(seat_limit between 1 and 10),
 created_at timestamptz not null default now()
);
create table if not exists public.rsvps(
 id uuid primary key default gen_random_uuid(),
 invitation_id uuid not null references public.invitations(id) on delete cascade,
 guest_name text not null check(char_length(trim(guest_name)) between 2 and 120),
 attending boolean not null,
 party_size integer not null default 1 check(party_size between 1 and 10),
 message text,
 updated_at timestamptz not null default now(),
 unique(invitation_id)
);
alter table public.invitations enable row level security;
alter table public.rsvps enable row level security;
revoke all on public.invitations from anon,authenticated;
revoke all on public.rsvps from anon,authenticated;

create or replace function public.resolve_invitation(p_token text)
returns table(token text,honoree text,seat_limit integer,guest_name text,attending boolean,party_size integer,message text)
language sql security definer set search_path=public as $$
 select i.token,i.honoree,i.seat_limit,r.guest_name,r.attending,r.party_size,r.message
 from public.invitations i left join public.rsvps r on r.invitation_id=i.id
 where i.token=lower(trim(p_token)) limit 1;
$$;

create or replace function public.save_rsvp(p_token text,p_guest_name text,p_attending boolean,p_party_size integer default 1,p_message text default null)
returns table(ok boolean,guest_name text,attending boolean,party_size integer,message text)
language plpgsql security definer set search_path=public as $$
declare v public.invitations%rowtype;
begin
 select * into v from public.invitations where token=lower(trim(p_token));
 if not found then raise exception 'INVITATION_NOT_FOUND'; end if;
 if p_party_size<1 or p_party_size>v.seat_limit then raise exception 'PARTY_SIZE_EXCEEDS_LIMIT'; end if;
 if char_length(trim(p_guest_name))<2 then raise exception 'INVALID_NAME'; end if;
 insert into public.rsvps(invitation_id,guest_name,attending,party_size,message)
 values(v.id,trim(p_guest_name),p_attending,p_party_size,nullif(trim(p_message),''))
 on conflict(invitation_id) do update set guest_name=excluded.guest_name,attending=excluded.attending,party_size=excluded.party_size,message=excluded.message,updated_at=now();
 return query select true,trim(p_guest_name),p_attending,p_party_size,nullif(trim(p_message),'');
end;
$$;

grant execute on function public.resolve_invitation(text) to anon,authenticated;
grant execute on function public.save_rsvp(text,text,boolean,integer,text) to anon,authenticated;

-- Generate exactly 60 Cándida invitations and 40 Alberto invitations.
insert into public.invitations(honoree,seat_limit)
select 'candida',1 from generate_series(1,60);
insert into public.invitations(honoree,seat_limit)
select 'alberto',1 from generate_series(1,40);

-- Admin account: create the host in Supabase Auth first.
-- The function only returns data when the signed-in email equals p_email.
create or replace function public.admin_overview(p_email text)
returns table(token text,honoree text,seat_limit integer,guest_name text,attending boolean,party_size integer,message text,updated_at timestamptz)
language sql security definer set search_path=public as $$
 select i.token,i.honoree,i.seat_limit,r.guest_name,r.attending,r.party_size,r.message,r.updated_at
 from public.invitations i left join public.rsvps r on r.invitation_id=i.id
 where lower(coalesce(auth.jwt()->>'email',''))=lower(trim(p_email))
 order by case when i.honoree='candida' then 0 else 1 end,i.token;
$$;
grant execute on function public.admin_overview(text) to authenticated;
