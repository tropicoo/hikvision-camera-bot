# Release info

Version: 1.7

Release date: October 19, 2022

# Important
1. Add a new config variable to `config.json` for each of your cameras.

# New features
1. Added new authentication config variable `type` in `auth` section.
Could be one of `basic`, `digest`, or `digest_cached`. Default is `digest_cached`.
```json
"auth": {
  "user": "dummy-user",
  "password": "dummy-password",
  "type": "digest_cached"
}
```

# Misc
N/A
