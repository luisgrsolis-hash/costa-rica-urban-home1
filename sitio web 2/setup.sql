create table if not exists public.properties (
  id text primary key,
  title_es text not null,
  title_en text not null,
  price numeric not null,
  type text not null,
  location text not null,
  beds numeric default 0,
  baths numeric default 0,
  area text,
  image text not null,
  description text,
  description_en text,
  featured boolean default false,
  status text default 'active',
  created_at timestamptz default now()
);

alter table public.properties enable row level security;

insert into storage.buckets (id, name, public)
values ('property-images', 'property-images', true)
on conflict (id) do update set public = excluded.public;
