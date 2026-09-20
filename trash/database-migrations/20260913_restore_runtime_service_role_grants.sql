-- Restore the server-only bot role after public access hardening.
-- This intentionally grants only tables confirmed by production runtime logs.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.economy,
  public.levels,
  public.giveaways,
  public.temproles,
  public.role_income,
  public.tempvoice_setup_msg,
  public.user_inventory,
  public.automod_config,
  public.reaction_roles,
  public.shop_stock,
  public.leveling_config,
  public.leveling_exceptions,
  public.staff_config,
  public.marriages,
  public.adoptions
TO service_role;

NOTIFY pgrst, 'reload schema';
