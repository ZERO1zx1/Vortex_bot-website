"""Explore supabase-py and postgrest API for SQL execution capability."""
import inspect

lines = []

# Check supabase client
try:
    from supabase import create_client
    from supabase._sync.client import Client, ClientOptions
    lines.append("=== ClientOptions source ===")
    lines.append(inspect.getsource(ClientOptions))
except Exception as e:
    lines.append(f"ClientOptions inspect failed: {e}")

# Check postgrest
lines.append("\n=== PostgREST exported names ===")
import postgrest
lines.append(f"postgrest.__all__ = {getattr(postgrest, '__all__', 'no __all__')}")
lines.append(f"postgrest dir: {sorted(postgrest.__all__ if hasattr(postgrest, '__all__') else [x for x in dir(postgrest) if not x.startswith('_')])}")

# Try to instantiate and inspect postgrest client
try:
    from postgrest import PostgRESTClient
    lines.append("\n=== PostgRESTClient callable methods ===")
    for name in dir(PostgRESTClient):
        if not name.startswith('_'):
            attr = getattr(PostgRESTClient, name)
            if callable(attr):
                lines.append(f"  {name}")
    # Check session
    lines.append(f"\nsession type: {type(PostgRESTClient.session)}")
    session_cls = PostgRESTClient.session
    if hasattr(session_cls, '__func__'):
        lines.append(f"session descriptor returns: {type(session_cls.__func__(PostgRESTClient))}")
except Exception as e:
    lines.append(f"PostgRESTClient inspect failed: {e}")

# Check what httpx session the supabase client uses
try:
    from supabase import create_client
    client = create_client("https://example.supabase.co", "test")
    pg = client.postgrest
    lines.append(f"\npostgrest type: {type(pg)}")
    lines.append(f"postgrest session type: {type(pg.session)}")
    if hasattr(pg.session, '_transport'):
        lines.append(f"session has _transport")
    # Check for any HTTP method we can use
    sess = pg.session
    lines.append(f"Session methods: {[m for m in dir(sess) if not m.startswith('_') and callable(getattr(sess, m))]}")
except Exception as e:
    lines.append(f"Client session inspect failed: {e}")

with open("supabase_api_output.txt", "w") as f:
    f.write("\n".join(str(l) for l in lines))
