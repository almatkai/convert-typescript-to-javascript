# Source from the selected clone root; all mutable QA state remains in v2.
export HOME="$PWD/v2/.qa/home" TMPDIR="$PWD/v2/.qa/tmp" CARGO_HOME="$PWD/v2/.qa/cargo" npm_config_cache="$PWD/v2/.qa/npm" XDG_CACHE_HOME="$PWD/v2/.qa/cache" CARGO_TARGET_DIR="$PWD/v2/target"
export RUSTUP_HOME=/Users/almat/.rustup
export CARGO_NET_GIT_FETCH_WITH_CLI=true
mkdir -p "$HOME" "$TMPDIR" "$CARGO_HOME" "$npm_config_cache" "$XDG_CACHE_HOME"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$PWD/v2/.qa/pycache" RUSTUP_AUTO_INSTALL=0
