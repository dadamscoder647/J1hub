# J1hub

## Rate limit key prefix

`create_app` now uses a deterministic `RATELIMIT_KEY_PREFIX` by default: `<app_import_name>:<environment>`.

- Override explicitly with `RATELIMIT_KEY_PREFIX` if you need a custom namespace.
- For test-only randomization behavior, set `RATELIMIT_RANDOM_KEY_PREFIX_FOR_TESTS=true`.

Examples:

```bash
export RATELIMIT_KEY_PREFIX=j1hub:staging
# or for test isolation only
export RATELIMIT_RANDOM_KEY_PREFIX_FOR_TESTS=true
```

