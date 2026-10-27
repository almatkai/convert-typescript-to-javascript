//! Effects and frozen recovery ownership are outside SDK transactional state.
use crate::compiler::{convert, MAX_OUTPUT};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    future::Future,
    sync::{Arc, Mutex},
    task::{Context, Waker},
    time::Duration,
};
use tezbar_extension_sdk::{
    no_view, unchanged, view, BoxFuture, CommandConcurrency, CoreResult, Extension,
    ExtensionContext,
};

pub const ID: &str = "com.tezbar.native.convert-typescript-to-javascript";
pub const COMMANDS: &[&str] = &["paste-from-clipboard", "copy-to-clipboard"];
const MAX_SESSIONS: usize = 128;
const RPC_TIMEOUT: Duration = Duration::from_secs(10);
type Sessions = Arc<Mutex<HashMap<String, Arc<Mutex<Frozen>>>>>;

#[derive(Clone, Copy)]
enum Effect {
    Copy,
    Paste,
}
impl Effect {
    fn method(self) -> &'static str {
        match self {
            Self::Copy => "host.clipboard.write",
            Self::Paste => "host.clipboard.pasteText",
        }
    }
    fn success(self) -> &'static str {
        match self {
            Self::Copy => "Copied code to clipboard",
            Self::Paste => "Pasted JavaScript",
        }
    }
    fn label(self) -> &'static str {
        match self {
            Self::Copy => "Copy",
            Self::Paste => "Paste",
        }
    }
}
struct Frozen {
    owner: ExtensionContext,
    code: String,
    effect: Effect,
    token: u64,
    in_flight: bool,
    uncertain: bool,
}

#[derive(Default)]
pub struct Adapter {
    sessions: Sessions,
}

/// A cancelled/failed open is removed by the SDK without adapter disposal.
/// This guard removes the adapter allocation too, even if acquisition/effect awaits
/// are dropped. Successful recovery views explicitly keep their allocation.
struct Opening {
    sessions: Sessions,
    id: String,
    keep: bool,
}
impl Drop for Opening {
    fn drop(&mut self) {
        if !self.keep {
            self.sessions.lock().unwrap().remove(&self.id);
        }
    }
}
/// Token consumption and dispatch intent survive SDK staged-state rollback.
struct Attempt {
    frozen: Arc<Mutex<Frozen>>,
}
impl Drop for Attempt {
    fn drop(&mut self) {
        self.frozen.lock().unwrap().in_flight = false;
    }
}

fn cancelled_now(ctx: &ExtensionContext) -> bool {
    let future = ctx.cancelled();
    std::pin::pin!(future)
        .poll(&mut Context::from_waker(Waker::noop()))
        .is_ready()
}
pub fn positive_ack(value: &Value) -> bool {
    let Some(object) = value.as_object() else {
        return false;
    };
    object.get("ok") == Some(&Value::Bool(true))
        && object.keys().all(|key| key == "ok" || key == "message")
        && object.get("message").is_none_or(Value::is_string)
}

fn recovery(frozen: &Frozen) -> Value {
    // Code is encoded as a JSON string, never interpolated into executable HTML.
    // The fixed fence contains only escaped JSON (including escaped backticks).
    let quoted = serde_json::to_string(&frozen.code)
        .unwrap()
        .replace('`', "\\u0060");
    let warning = format!("{} outcome is unconfirmed. It may already have happened. Retrying can duplicate the effect. The exact converted bytes below are frozen; retry does not read or convert again.", frozen.effect.label());
    let markdown = format!("{warning}\n\nFrozen JavaScript as a JSON string ({} UTF-8 bytes):\n\n```json\n{quoted}\n```", frozen.code.len());
    let actions = if frozen.in_flight {
        vec![]
    } else {
        vec![json!({
            "id":format!("retry:{}", frozen.token),
            "title":format!("Retry {} — may duplicate", frozen.effect.label()),
            "kind":"action"
        })]
    };
    let mut value = view(
        "JavaScript delivery unconfirmed",
        json!({"type":"Detail","props":{"markdown":markdown}}),
        actions,
    );
    value["refreshMs"] = Value::Null;
    value
}

async fn rpc(ctx: &ExtensionContext, method: &str, params: Value) -> CoreResult {
    tokio::time::timeout(RPC_TIMEOUT, ctx.host(method, params))
        .await
        .map_err(|_| "Host response timed out".to_owned())?
}

impl Adapter {
    async fn deliver(
        &self,
        ctx: &ExtensionContext,
        frozen: Arc<Mutex<Frozen>>,
        expected: u64,
    ) -> CoreResult {
        let (method, code, success) = {
            let mut f = frozen.lock().unwrap();
            if f.in_flight || f.token != expected {
                return Ok(unchanged());
            }
            // Consumed before any await, outside staged Value. Once the request
            // may dispatch, every failure/cancellation is conservatively unknown.
            f.token = f.token.checked_add(1).ok_or("Recovery token exhausted")?;
            f.in_flight = true;
            f.uncertain = true;
            (f.effect.method(), f.code.clone(), f.effect.success())
        };
        let attempt = Attempt {
            frozen: frozen.clone(),
        };
        let result = rpc(ctx, method, json!({"text":code})).await;
        drop(attempt);
        if result.as_ref().is_ok_and(positive_ack) {
            frozen.lock().unwrap().uncertain = false;
            Ok(no_view(success))
        } else {
            // Do not echo arbitrary host error strings or unknown result fields.
            Ok(recovery(&frozen.lock().unwrap()))
        }
    }
}

impl Extension for Adapter {
    fn id(&self) -> &'static str {
        ID
    }
    fn version(&self) -> &'static str {
        "2.0.0"
    }
    fn commands(&self) -> &'static [&'static str] {
        COMMANDS
    }
    fn concurrency(&self, _: &str) -> CommandConcurrency {
        CommandConcurrency::RejectWhileBusy
    }
    fn handle<'a>(
        &'a self,
        ctx: &'a ExtensionContext,
        command: &'a str,
        operation: &'a str,
        payload: &'a Value,
        _: &'a mut Value,
    ) -> BoxFuture<'a, CoreResult> {
        Box::pin(async move {
            let id = payload["sessionId"]
                .as_str()
                .filter(|s| !s.is_empty() && s.len() <= 256)
                .ok_or("Invalid session id")?;
            if operation == "extension:dispose-session" {
                self.sessions.lock().unwrap().remove(id);
                return Ok(json!({"disposed":true}));
            }
            if operation == "extension:run-command" {
                let effect = match command {
                    "paste-from-clipboard" => Effect::Paste,
                    "copy-to-clipboard" => Effect::Copy,
                    _ => return Err("Unknown command".into()),
                };
                // Reserve before acquisition to keep all concurrent opens bounded.
                let frozen = Arc::new(Mutex::new(Frozen {
                    owner: ctx.clone(),
                    code: String::new(),
                    effect,
                    token: 0,
                    in_flight: false,
                    uncertain: false,
                }));
                {
                    let mut sessions = self.sessions.lock().unwrap();
                    // SDK can cancel after adapter return but before state commit.
                    // Prune those orphaned opens on the next ordinary request;
                    // no detached watcher/timer or dispose callback is required.
                    sessions.retain(|_, entry| !cancelled_now(&entry.lock().unwrap().owner));
                    if sessions.len() >= MAX_SESSIONS || sessions.contains_key(id) {
                        return Err("Native session capacity reached".into());
                    }
                    sessions.insert(id.to_owned(), frozen.clone());
                }
                let mut opening = Opening {
                    sessions: self.sessions.clone(),
                    id: id.to_owned(),
                    keep: false,
                };
                let (method, params) = match effect {
                    Effect::Paste => ("host.clipboard.read", json!({"format":"content"})),
                    Effect::Copy => ("host.selection.read", json!({"kind":"text"})),
                };
                let acquired = rpc(ctx, method, params).await;
                // Content mode is an explicit host prerequisite. Legacy STRING
                // responses fail closed: they cannot certify the file guard.
                let Some(source) = acquired
                    .as_ref()
                    .ok()
                    .and_then(|value| match effect {
                        Effect::Copy => value.as_str(),
                        Effect::Paste => clipboard_content_text(value),
                    })
                    .filter(|s| !s.is_empty())
                else {
                    return Ok(no_view("No text found in clipboard"));
                };
                let code = match convert(source) {
                    Ok(code) => code,
                    Err(message) => return Ok(no_view(message)),
                };
                debug_assert!(code.len() <= MAX_OUTPUT);
                frozen.lock().unwrap().code = code;
                let result = self.deliver(ctx, frozen, 0).await?;
                opening.keep = result["mode"] == "view";
                return Ok(result);
            }
            let frozen = self.sessions.lock().unwrap().get(id).cloned();
            let Some(frozen) = frozen else {
                return Ok(unchanged());
            };
            if operation == "extension:refresh-session" {
                let f = frozen.lock().unwrap();
                return Ok(if f.uncertain {
                    recovery(&f)
                } else {
                    unchanged()
                });
            }
            if operation == "extension:invoke-action" {
                let Some(token) = payload["actionId"]
                    .as_str()
                    .and_then(|s| s.strip_prefix("retry:"))
                    .and_then(|s| s.parse::<u64>().ok())
                else {
                    return Ok(unchanged());
                };
                if !frozen.lock().unwrap().uncertain {
                    return Ok(unchanged());
                }
                let result = self.deliver(ctx, frozen, token).await?;
                if result["mode"] == "no-view" {
                    self.sessions.lock().unwrap().remove(id);
                }
                return Ok(result);
            }
            Ok(unchanged())
        })
    }
}

fn clipboard_content_text(value: &Value) -> Option<&str> {
    let object = value.as_object()?;
    if object.len() != 2 || object.get("hasFiles")?.as_bool()? {
        return None;
    }
    object.get("text")?.as_str()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn closed_positive_ack() {
        for value in [
            json!(null),
            json!(true),
            json!({}),
            json!({"ok":false}),
            json!({"ok":true,"error":"no"}),
            json!({"ok":true,"message":null}),
            json!({"ok":true,"other":1}),
        ] {
            assert!(!positive_ack(&value));
        }
        assert!(positive_ack(&json!({"ok":true})));
        assert!(positive_ack(&json!({"ok":true,"message":"done"})));
    }
}
